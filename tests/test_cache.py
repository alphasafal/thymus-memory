from thymus.llm import CachedLLM


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
