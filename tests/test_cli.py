from thymus.cli import preflight


class Fixed:
    name = "fixed"

    def __init__(self, reply):
        self.reply = reply

    def complete(self, system, prompt, schema=None):
        return self.reply


def test_preflight_accepts_a_short_correct_answer():
    assert preflight(Fixed("Paris")) is None


def test_preflight_catches_leaked_reasoning():
    leaked = "Hmm, the user is asking about the capital of France. I recall that Paris is the capital."
    assert "failed the sanity check" in preflight(Fixed(leaked))
    assert preflight(Fixed("Okay, let me think about this question carefully first.")) is not None
