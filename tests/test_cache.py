import pytest

from thymus.llm import CachedLLM, CallBudgetExceeded


class Counting:
    name = "counting:model"

    def __init__(self):
        self.calls = 0

    def complete(self, system, prompt, schema=None):
        self.calls += 1
        return f"answer {self.calls}"


def test_cache_returns_stored_answers_and_survives_restart(tmp_path):
    inner = Counting()
    first = CachedLLM(inner, tmp_path)
    assert first.complete("sys", "q1") == "answer 1"
    assert first.complete("sys", "q1") == "answer 1"
    assert first.complete("sys", "q2", schema={"type": "object"}) == "answer 2"
    assert inner.calls == 2

    reopened = CachedLLM(inner, tmp_path)
    assert reopened.complete("sys", "q1") == "answer 1"
    assert inner.calls == 2


def test_call_cap_stops_new_calls_but_keeps_serving_the_cache(tmp_path):
    inner = Counting()
    capped = CachedLLM(inner, tmp_path, max_new_calls=1)
    assert capped.complete("sys", "q1") == "answer 1"
    assert capped.exhausted
    assert capped.complete("sys", "q1") == "answer 1"  # cached answers are still free
    with pytest.raises(CallBudgetExceeded):
        capped.complete("sys", "q2")


def test_post_json_turns_dropped_connections_into_llm_unavailable(monkeypatch):
    import http.client
    import urllib.request

    from thymus import llm as llm_module

    calls = {"n": 0}

    def drop(*args, **kwargs):
        calls["n"] += 1
        raise http.client.RemoteDisconnected("Remote end closed connection without response")

    monkeypatch.setattr(urllib.request, "urlopen", drop)
    monkeypatch.setattr(llm_module.time, "sleep", lambda s: None)
    with pytest.raises(llm_module.LLMUnavailable):
        llm_module.post_json("http://localhost:1/api/chat", {}, timeout=1, retries=2)
    assert calls["n"] == 3
