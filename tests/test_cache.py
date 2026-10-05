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
