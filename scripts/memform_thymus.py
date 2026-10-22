"""The thymus gate as a MemForm write-time defense (Pan et al. 2026, github.com/opanhw/memform-code, MIT).

Usage (MemForm installed, e.g. `pip install -e data/memform-code`):
    python scripts/memform_thymus.py run-defense --defense all --cases <cases.jsonl> ...
Same arguments as `python -m memform run-defense`; this adds a defense named `thymus` to
MemForm's registry (and to `--defense all`) without changing MemForm's code.

MemForm hides provenance from every defense (it is a scoring label there), and the thymus
gate's main mechanism is provenance. So each record is treated as coming from its own unknown,
unauthenticated source, the most conservative reading of the gate's rules:
- a record that is not a plain fact (a preference or an instruction, e.g. a "reusable decision
  rule" stated as a command) is rejected: untrusted content may not speak for the user;
- a record that contradicts an earlier record of the case is contested, and contested claims are
  withheld from the model (quarantined here: MemForm has no user to disclose them to);
- everything else is kept. No record can replace another: no source is authenticated.
Model calls go through thymus' own Ollama client and cache (model: THYMUS_MEMFORM_MODEL).
"""

from __future__ import annotations

import os
import sys
import time
import types
from pathlib import Path

# MemForm's release re-exports memform.freeform.build, which the authors withheld with the case
# construction pipeline; evaluation never calls it. A stand-in keeps their code unmodified.
_build = types.ModuleType("memform.freeform.build")
_build.build_freeform_case = _build.validate_freeform_case = None
sys.modules.setdefault("memform.freeform.build", _build)

from memform.defenses import DEFENSE_REGISTRY  # noqa: E402
from memform.defenses.common import DefenseContext, DefenseDecision, MemoryDefense, MemoryItem  # noqa: E402

from thymus.embed import MemoEmbedder, OllamaEmbedder  # noqa: E402
from thymus.gates import make_gate  # noqa: E402
from thymus.llm import CachedLLM, OllamaLLM  # noqa: E402
from thymus.memory import Candidate, MemoryStore  # noqa: E402


def record_text(item: MemoryItem) -> str:
    if item.context or item.action or item.outcome:
        parts = [item.text or ""]
        parts += [f"Situation: {item.context}" if item.context else "", f"Action taken: {item.action}" if item.action else "",
                  f"Outcome: {item.outcome}" if item.outcome else ""]
        return " ".join(p for p in parts if p).strip()
    return item.text


class ThymusDefense(MemoryDefense):
    name = "thymus"
    display_name = "thymus (provenance unknown)"
    prompt_version = "v3"

    def __init__(self, model=None, threshold: float = 0.5, **kwargs):
        super().__init__(model=model, threshold=threshold, **kwargs)
        llm = CachedLLM(OllamaLLM(os.environ.get("THYMUS_MEMFORM_MODEL", "qwen3:4b-instruct")), Path(".cache/llm"))
        self.gate = make_gate("thymus-v3", llm)
        self.embedder = MemoEmbedder(OllamaEmbedder("nomic-embed-text"))

    def filter_memory(self, memory: MemoryItem, context: DefenseContext | None = None) -> DefenseDecision:
        return self.process_memories([memory], context)[0]

    def process_memories(self, memories: list[MemoryItem], context: DefenseContext | None = None) -> list[DefenseDecision]:
        store = MemoryStore(self.embedder)
        out = []
        for i, item in enumerate(memories):
            start = time.perf_counter()
            text = record_text(item)
            candidate = Candidate(text, "tool", f"record:{i}", "agent", i + 1, authenticated=False)
            decision = self.gate.review(candidate, store)
            if decision.action == "reject":
                action, accepted = "reject", False
            elif decision.contradicts or decision.action == "quarantine":
                action, accepted = "quarantine", False
                store.add(candidate, status="quarantined")
            else:
                action, accepted = "keep", True
                store.add(candidate, trust=decision.trust)
            out.append(DefenseDecision(memory_id=item.memory_id, accepted=accepted, action=action,
                                       reason=decision.reason, original_text=item.text,
                                       latency=time.perf_counter() - start))
        return out


def main() -> None:
    """`run-langchain ...` (undefended agent) or `run-defense ...` (defenses, thymus included)."""
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.argv = [f"memform {command}", *sys.argv[2:]]
    if command == "run-langchain":
        from memform.eval.core import main as run
    elif command == "run-defense":
        import memform.eval.defense as runner

        DEFENSE_REGISTRY["thymus"] = ThymusDefense
        runner.DEFENSE_NAMES = tuple(DEFENSE_REGISTRY)
        run = runner.main
    else:
        raise SystemExit("usage: memform_thymus.py run-langchain|run-defense <memform arguments>")
    run()


if __name__ == "__main__":
    main()
