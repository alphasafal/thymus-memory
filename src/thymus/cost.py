"""What a gate costs: model calls, approximate tokens and time, by the job each call does.

Wrap every model once with ``CountingLLM`` (outside the cache) and share one ``Usage``. A call's
job is recognised from its system prompt, so no gate or agent code has to report anything.
Tokens are estimated as characters / 4 (the same estimate for every model and gate, so
comparisons between gates are fair); seconds are only meaningful for uncached calls.
"""

from __future__ import annotations

import time
from collections import defaultdict

from thymus.llm import LLM

# Jobs that exist only because of a gate: the rest (extract, answer) every memory agent does.
GATE_ROLES = ("classify", "conflict", "verify")


def _roles() -> dict[str, str]:
    from thymus.agent import ANSWER_SYSTEM, EXTRACT_SYSTEM
    from thymus.claims import CLAIM_SYSTEM
    from thymus.conflicts import CONFLICT_SYSTEM, CONFLICT_SYSTEM_SAME_SUBJECT, VERIFY_WORDINGS

    roles = {ANSWER_SYSTEM: "answer", EXTRACT_SYSTEM: "extract", CLAIM_SYSTEM: "classify",
             CONFLICT_SYSTEM: "conflict", CONFLICT_SYSTEM_SAME_SUBJECT: "conflict"}
    roles.update({system: "verify" for system, _ in VERIFY_WORDINGS.values()})
    return roles


class Usage:
    """Running totals per job: calls, input and output characters, seconds."""

    def __init__(self) -> None:
        self.totals: dict[str, list[float]] = defaultdict(lambda: [0, 0, 0, 0.0])

    def record(self, role: str, prompt_chars: int, output_chars: int, seconds: float) -> None:
        t = self.totals[role]
        t[0] += 1
        t[1] += prompt_chars
        t[2] += output_chars
        t[3] += seconds

    def snapshot(self) -> dict[str, tuple]:
        return {role: tuple(t) for role, t in self.totals.items()}

    def since(self, before: dict[str, tuple]) -> dict[str, dict]:
        """Usage added after ``before`` was taken, as {role: {calls, tokens_in, tokens_out, seconds}}."""
        out = {}
        for role, t in self.totals.items():
            b = before.get(role, (0, 0, 0, 0.0))
            calls = t[0] - b[0]
            if calls:
                out[role] = {"calls": int(calls), "tokens_in": round((t[1] - b[1]) / 4),
                             "tokens_out": round((t[2] - b[2]) / 4), "seconds": round(t[3] - b[3], 3)}
        return out


class CountingLLM:
    """Passes calls through and records each one in ``usage`` under its job."""

    def __init__(self, inner: LLM, usage: Usage):
        self.inner = inner
        self.name = inner.name
        self.usage = usage
        self._roles = _roles()

    def complete(self, system: str, prompt: str, schema: dict | None = None) -> str:
        start = time.perf_counter()
        response = self.inner.complete(system, prompt, schema)
        role = self._roles.get(system, "judge")  # every other prompt in a run grades replies
        self.usage.record(role, len(system) + len(prompt), len(response), time.perf_counter() - start)
        return response

    def __getattr__(self, attr: str):  # e.g. CachedLLM.exhausted
        return getattr(self.inner, attr)


def gate_overhead(cost: dict[str, dict]) -> dict[str, float]:
    """Calls and tokens spent on gate-only jobs in one scenario."""
    jobs = [cost[r] for r in GATE_ROLES if r in cost]
    return {"calls": sum(j["calls"] for j in jobs),
            "tokens": sum(j["tokens_in"] + j["tokens_out"] for j in jobs),
            "seconds": sum(j["seconds"] for j in jobs)}
