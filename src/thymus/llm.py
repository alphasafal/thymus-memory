"""Chat model backends.

Every backend exposes one method, ``complete(system, prompt, schema=None) -> str``.
When ``schema`` is given the backend must return JSON matching it.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Protocol


class LLMError(RuntimeError):
    """A model call failed or was refused."""


class LLMUnavailable(LLMError):
    """The model server could not be reached even after retries; the run should stop
    (and resume later from the cache) rather than record every remaining scenario as failed."""


class LLM(Protocol):
    name: str

    def complete(self, system: str, prompt: str, schema: dict | None = None) -> str: ...


def post_json(url: str, body: dict, timeout: float, retries: int = 5) -> Any:
    """POST JSON, retrying connection failures and server errors with backoff (about four
    minutes in total), so a model server that restarts mid-run does not end the run."""
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == retries:
                detail = e.read().decode(errors="replace")[:300]
                raise LLMError(f"request to {url} failed with HTTP {e.code}: {detail}") from e
        except (urllib.error.URLError, http.client.HTTPException, ConnectionError, TimeoutError) as e:
            if attempt == retries:
                raise LLMUnavailable(f"request to {url} failed: {e}. Is `ollama serve` running?") from e
        time.sleep(min(120, 8 * 2**attempt))
    raise AssertionError("unreachable")


class OllamaLLM:
    """A local model served by Ollama. Free to run; quality depends on model size."""

    def __init__(
        self, model: str, host: str = "http://localhost:11434", timeout: float = 300, max_tokens: int = 768,
        num_ctx: int | None = None,
    ):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.max_tokens = max_tokens
        # Ollama's default context window is short and it drops the start of longer prompts
        # without an error; long-memory benchmarks set this (THYMUS_OLLAMA_CTX or the caller).
        self.num_ctx = num_ctx or (int(os.environ["THYMUS_OLLAMA_CTX"]) if os.environ.get("THYMUS_OLLAMA_CTX") else None)
        self.name = f"ollama:{model}"
        self._can_think: bool | None = None

    def _supports_thinking(self) -> bool:
        if self._can_think is None:
            info = post_json(f"{self.host}/api/show", {"model": self.model}, self.timeout)
            self._can_think = "thinking" in info.get("capabilities", [])
        return self._can_think

    def complete(self, system: str, prompt: str, schema: dict | None = None) -> str:
        body: dict[str, Any] = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            # num_predict caps runaway generations: small models sometimes repeat text
            # until the request times out (seen on Hindi inputs), which stalls a whole run.
            "options": {"temperature": 0, "seed": 0, "num_predict": self.max_tokens},
        }
        if self.num_ctx:
            body["options"]["num_ctx"] = self.num_ctx
        if schema is not None:
            body["format"] = schema
        if self._supports_thinking():
            body["think"] = False  # reasoning models: answer directly, keeps runs fast
        return post_json(f"{self.host}/api/chat", body, self.timeout)["message"]["content"]


def find_claude_binary() -> str:
    """The Claude Code CLI: $THYMUS_CLAUDE_BIN, `claude` on PATH, or the newest copy
    bundled with the Claude desktop app on macOS."""
    if os.environ.get("THYMUS_CLAUDE_BIN"):
        return os.environ["THYMUS_CLAUDE_BIN"]
    on_path = shutil.which("claude")
    if on_path:
        return on_path
    pattern = "Library/Application Support/Claude/claude-code/*/*/claude.app/Contents/MacOS/claude"
    bundled = sorted(
        Path.home().glob(pattern),
        key=lambda p: tuple(int(x) for x in p.parts[-6].split(".") if x.isdigit()),
    )
    if bundled:
        return str(bundled[-1])
    raise LLMError("Claude Code CLI not found; install it or set THYMUS_CLAUDE_BIN")


# Messages the Claude Code and Codex CLIs print when a subscription's usage limit is hit.
_PLAN_LIMIT = re.compile(
    r"usage limit|rate.?limit|hit your limit|limit reached|quota|too many requests|resource.?exhausted|\b429\b", re.I
)


def _cli_failure(name: str, text: str) -> LLMError:
    """A plan usage limit stops the run (rerun after it resets); anything else fails one call."""
    if _PLAN_LIMIT.search(text):
        return LLMUnavailable(f"{name} hit the plan's usage limit (rerun after it resets): {text[-300:]}")
    return LLMError(f"{name} failed: {text[-300:]}")


class ClaudeCodeLLM:
    """Claude through the Claude Code CLI in print mode, so calls use the user's Claude
    subscription instead of a paid API key. Log the CLI in once first (run it, then /login).
    Each call starts a process, so it is slower than the API, and it counts toward the
    plan's usage limits. Best used for grading, not for running the agent."""

    def __init__(self, model: str | None = None, binary: str | None = None, timeout: float = 300):
        self.binary = binary or find_claude_binary()
        self.model = model
        self.timeout = timeout
        self.name = f"claude-code:{model or 'default'}"

    def complete(self, system: str, prompt: str, schema: dict | None = None) -> str:
        command = [
            self.binary, "-p", prompt,
            "--output-format", "json",
            "--system-prompt", system,
            "--tools", "",
            "--strict-mcp-config",
            "--setting-sources", "",
            "--no-session-persistence",
        ]
        if self.model:
            command += ["--model", self.model]
        if schema is not None:
            command += ["--json-schema", json.dumps(schema)]
        try:
            done = subprocess.run(
                command, capture_output=True, text=True, timeout=self.timeout, cwd=tempfile.gettempdir()
            )
        except subprocess.TimeoutExpired as e:
            raise LLMError(f"{self.name} timed out after {self.timeout}s") from e
        try:
            data = json.loads(done.stdout)
        except json.JSONDecodeError:
            raise _cli_failure(self.name, f"no JSON: {done.stderr or done.stdout}") from None
        if data.get("is_error"):
            raise _cli_failure(self.name, str(data.get("result")))
        if schema is not None and data.get("structured_output") is not None:
            return json.dumps(data["structured_output"])
        return data.get("result", "")


# Models that accept server-side refusal fallbacks (fallbacks="default").
_FALLBACK_MODELS = {"claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}
# Models that reject output_config.effort.
_NO_EFFORT_MODELS = {"claude-haiku-4-5"}


# Anthropic first-party API prices, US$ per million tokens (input, output), October 2026.
_ANTHROPIC_PRICES = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}
# Dollars spent through AnthropicLLM in this process, across instances (gate + agent + judge
# may be separate instances of the same model). THYMUS_ANTHROPIC_BUDGET_USD caps it: the run
# stops with CallBudgetExceeded, cached work is kept, and a rerun resumes from the cache.
_anthropic_spend_usd = 0.0


def anthropic_spend() -> float:
    return _anthropic_spend_usd


class AnthropicLLM:
    """Claude via the official SDK. Needs `uv sync --extra anthropic` and credentials
    (ANTHROPIC_API_KEY or an `ant auth login` profile). Every call costs money."""

    def __init__(self, model: str = "claude-opus-5-5", effort: str = "low", max_tokens: int = 16000):
        import anthropic

        self._client = anthropic.Anthropic()
        self.model = model
        self.effort = effort
        self.max_tokens = max_tokens
        self.name = f"anthropic:{model}"
        budget = os.environ.get("THYMUS_ANTHROPIC_BUDGET_USD")
        self.budget_usd = float(budget) if budget else None

    def complete(self, system: str, prompt: str, schema: dict | None = None) -> str:
        output_config: dict[str, Any] = {}
        if self.model not in _NO_EFFORT_MODELS:
            output_config["effort"] = self.effort
        if schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": schema}
        extra: dict[str, Any] = {}
        if output_config:
            extra["output_config"] = output_config
        if self.model in _FALLBACK_MODELS:
            extra["betas"] = ["server-side-fallback-2026-07-01"]
            extra["fallbacks"] = "default"

        global _anthropic_spend_usd
        if self.budget_usd is not None and _anthropic_spend_usd >= self.budget_usd:
            raise CallBudgetExceeded(
                f"{self.name} spent ${_anthropic_spend_usd:.2f}, over the "
                f"${self.budget_usd:.2f} cap (THYMUS_ANTHROPIC_BUDGET_USD)")
        response = self._client.beta.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            **extra,
        )
        in_price, out_price = _ANTHROPIC_PRICES.get(self.model, (10.00, 50.00))
        usage = response.usage
        _anthropic_spend_usd += (usage.input_tokens * in_price + usage.output_tokens * out_price) / 1e6
        if response.stop_reason == "refusal":
            category = response.stop_details.category if response.stop_details else None
            raise LLMError(f"{self.name} refused (category: {category})")
        return next((b.text for b in response.content if b.type == "text"), "")


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _tagged(prompt: str, tag: str) -> str:
    match = re.search(rf"<{tag}[^>]*>\n?(.*?)\n?</{tag}>", prompt, re.DOTALL)
    return match.group(1).strip() if match else ""


class EchoLLM:
    """Offline stand-in for a maximally gullible model, used by tests and smoke runs.

    Extraction: stores every sentence of the <content> block as a memory.
    Answering: repeats the recalled <memories> lines verbatim.

    It relies on the tag layout of the prompts in ``thymus.agent``.
    """

    name = "echo"

    def complete(self, system: str, prompt: str, schema: dict | None = None) -> str:
        if schema is not None:
            content = _tagged(prompt, "content")
            sentences = [s.strip() for s in _SENTENCE_SPLIT.split(content) if s.strip()]
            return json.dumps({"memories": sentences})
        return _tagged(prompt, "memories") or "I don't know."


class CodexLLM:
    """GPT through OpenAI's Codex CLI (`codex exec`) signed in with a ChatGPT plan, so calls
    use the plan instead of a paid API key. Codex is a coding agent, so by default every call
    carries its own coding prompt and tool definitions (about 20k tokens). Here our system
    prompt replaces Codex's built-in instructions and its tools are switched off, which brings
    a call down to about 5k tokens. Calls still count toward the plan's 5-hour limits, so use
    it only for small, capped runs. It runs read-only in an empty folder and saves no session
    files."""

    # Codex features that add tools (and so prompt tokens) we never want here.
    DISABLED_FEATURES = (
        "apps", "browser_use", "browser_use_external", "computer_use", "goals", "image_generation",
        "multi_agent", "plugins", "shell_tool", "unified_exec", "view_image", "sleep_tool",
        "skill_search", "tool_suggest", "hooks",
    )

    def __init__(self, model: str | None = None, binary: str | None = None, timeout: float = 300):
        self.binary = binary or shutil.which("codex") or "codex"
        self.model = model
        self.timeout = timeout
        self.name = f"codex:{model or 'default'}"

    def complete(self, system: str, prompt: str, schema: dict | None = None) -> str:
        with tempfile.TemporaryDirectory() as workdir:
            out = Path(workdir) / "last.txt"
            instructions = Path(workdir) / "instructions.md"
            instructions.write_text(system)
            command = [
                self.binary, "exec", "--skip-git-repo-check", "--ephemeral", "--ignore-user-config",
                "-s", "read-only", "-C", workdir, "-o", str(out),
                "-c", f"model_instructions_file={json.dumps(str(instructions))}",
                "-c", 'web_search="disabled"',
            ]
            for feature in self.DISABLED_FEATURES:
                command += ["--disable", feature]
            if self.model:
                command += ["-m", self.model]
            if schema is not None:
                schema_file = Path(workdir) / "schema.json"
                schema_file.write_text(json.dumps(schema))
                command += ["--output-schema", str(schema_file)]
            command.append("-")
            try:
                done = subprocess.run(command, input=prompt, capture_output=True, text=True, timeout=self.timeout)
            except subprocess.TimeoutExpired as e:
                raise LLMError(f"{self.name} timed out after {self.timeout}s") from e
            if done.returncode != 0 or not out.exists():
                raise _cli_failure(self.name, done.stderr or done.stdout)
            return out.read_text().strip()


class GeminiCLILLM:
    """Gemini through Google's Gemini CLI signed in with a Google account (`gemini`, then
    "Login with Google"), so calls use the account's free quota instead of a paid API key.
    Our system prompt replaces the CLI's own (GEMINI_SYSTEM_MD) and each call runs in an
    empty folder. The CLI has no JSON-schema option, so structured calls ask for JSON in the
    prompt and the first JSON object in the reply is returned."""

    def __init__(self, model: str | None = None, binary: str | None = None, timeout: float = 300):
        self.binary = binary or shutil.which("gemini") or "gemini"
        self.model = model
        self.timeout = timeout
        self.name = f"gemini-cli:{model or 'default'}"

    def complete(self, system: str, prompt: str, schema: dict | None = None) -> str:
        if schema is not None:
            prompt += (
                "\n\nReply with only one JSON object that matches this JSON schema, and nothing else:\n"
                + json.dumps(schema)
            )
        with tempfile.TemporaryDirectory() as workdir:
            system_file = Path(workdir) / "system.md"
            system_file.write_text(system)
            command = [self.binary, "--output-format", "json", "--skip-trust"]  # runs in an empty temp folder
            if self.model:
                command += ["-m", self.model]
            env = {**os.environ, "GEMINI_SYSTEM_MD": str(system_file)}
            try:
                done = subprocess.run(
                    command, input=prompt, capture_output=True, text=True, timeout=self.timeout, cwd=workdir, env=env
                )
            except subprocess.TimeoutExpired as e:
                raise LLMError(f"{self.name} timed out after {self.timeout}s") from e
        try:  # the CLI may print log lines before its JSON
            data, _ = json.JSONDecoder().raw_decode(done.stdout[done.stdout.index("{"):])
        except ValueError:
            raise _cli_failure(self.name, done.stderr or done.stdout) from None
        if done.returncode != 0 or data.get("error"):
            raise _cli_failure(self.name, json.dumps(data.get("error")) + " " + done.stderr)
        reply = str(data.get("response", "")).strip()
        if schema is None:
            return reply
        match = re.search(r"\{.*\}", reply, re.DOTALL)
        if not match:
            raise LLMError(f"{self.name} returned no JSON object: {reply[:200]}")
        return match.group(0)


class CachedLLM:
    """Remembers every response on disk, keyed by model and full request.

    Local models run at temperature 0, so a repeated request gets the same answer anyway.
    Caching makes repeated work free (every gate starts a scenario with the same extraction
    calls), lets interrupted runs resume, and guarantees all gates see identical extractions,
    so differences between gates come from the gates alone.
    """

    def __init__(self, inner: LLM, cache_dir: Path, max_new_calls: int | None = None):
        self.inner = inner
        self.name = inner.name
        self.max_new_calls = max_new_calls  # hard cap on real model calls, e.g. for a paid plan
        self.new_calls = 0
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.path = cache_dir / (re.sub(r"[^A-Za-z0-9_.-]", "_", inner.name) + ".jsonl")
        self._cache: dict[str, str] = {}
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                if line.strip():
                    entry = json.loads(line)
                    self._cache[entry["key"]] = entry["response"]

    def complete(self, system: str, prompt: str, schema: dict | None = None) -> str:
        request = json.dumps([self.inner.name, system, prompt, schema], sort_keys=True)
        key = hashlib.sha256(request.encode()).hexdigest()
        if key not in self._cache:
            if self.exhausted:
                raise CallBudgetExceeded(f"{self.name}: reached the cap of {self.max_new_calls} new calls")
            self.new_calls += 1
            response = self.inner.complete(system, prompt, schema)
            self._cache[key] = response
            with self.path.open("a") as f:
                f.write(json.dumps({"key": key, "response": response}) + "\n")
        return self._cache[key]

    @property
    def exhausted(self) -> bool:
        return self.max_new_calls is not None and self.new_calls >= self.max_new_calls


class CallBudgetExceeded(LLMError):
    """The run hit its cap on new model calls; cached work is kept and a rerun resumes."""
