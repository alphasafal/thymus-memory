"""Chat model backends.

Every backend exposes one method, ``complete(system, prompt, schema=None) -> str``.
When ``schema`` is given the backend must return JSON matching it.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any, Protocol


class LLMError(RuntimeError):
    """A model call failed or was refused."""


class LLM(Protocol):
    name: str

    def complete(self, system: str, prompt: str, schema: dict | None = None) -> str: ...


def post_json(url: str, body: dict, timeout: float) -> Any:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())
    except urllib.error.URLError as e:
        raise LLMError(f"request to {url} failed: {e}. Is `ollama serve` running?") from e


class OllamaLLM:
    """A local model served by Ollama. Free to run; quality depends on model size."""

    def __init__(self, model: str, host: str = "http://localhost:11434", timeout: float = 300):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.name = f"ollama:{model}"

    def complete(self, system: str, prompt: str, schema: dict | None = None) -> str:
        body: dict[str, Any] = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "options": {"temperature": 0, "seed": 0},
        }
        if schema is not None:
            body["format"] = schema
        return post_json(f"{self.host}/api/chat", body, self.timeout)["message"]["content"]


# Models that accept server-side refusal fallbacks (fallbacks="default").
_FALLBACK_MODELS = {"claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}
# Models that reject output_config.effort.
_NO_EFFORT_MODELS = {"claude-haiku-4-5"}


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

        response = self._client.beta.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            **extra,
        )
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
