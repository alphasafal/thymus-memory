"""Guarantees of the thymus gate, checked on random write sequences.

The averages in the paper depend on models; these do not. Whatever the conflict detector
and claim classifier say (here: random answers), the gate must never

- let tool content replace a fact from a different origin or from the user,
- let a user replace what a different user told a shared assistant,
- store a preference or instruction from an untrusted tool origin,
- recall an untrusted memory without its source, or a contested one without saying so.

Models only decide *which* rule applies; these properties hold for every decision. They
assume origins are authentic (spoofing is measured separately in the benchmark).
"""

import random

import pytest

from thymus.embed import HashEmbedder
from thymus.gates import LabelOnlyGate, ThymusGate
from thymus.memory import Candidate, MemoryStore

TRUSTED = ("calendar:",)
TOOL_ORIGINS = ("email:a@shop.example", "email:b@lookalike.example", "web:reviews.example", "sms:VM-BANK", "calendar:work")
SPEAKERS = ("victim", "victim", "attacker")
KINDS = ("fact", "fact", "user_preference", "instruction")


class RandomConflicts:
    """Claims that a random subset of earlier active memories conflict (detector contract:
    only memories from earlier turns can conflict)."""

    def __init__(self, rng: random.Random):
        self.rng = rng

    def find(self, candidate, store):
        earlier = [m for m in store.all() if m.status == "active" and m.created_at < candidate.created_at]
        return [m for m in earlier if self.rng.random() < 0.3]


class RandomClaims:
    """Each candidate gets a random kind when it is made; the classifier reports it."""

    def __init__(self):
        self.kinds = {}

    def kind(self, text):
        return self.kinds[text]


def random_candidate(rng: random.Random, turn: int) -> Candidate:
    if rng.random() < 0.4:
        return Candidate(f"user fact {turn}", "user", "chat", rng.choice(SPEAKERS), turn)
    # One in four tool messages is a forged sender: the right origin, failed authentication.
    return Candidate(f"tool fact {turn}", "tool", rng.choice(TOOL_ORIGINS), "victim", turn, rng.random() > 0.25)


def untrusted(memory_or_candidate) -> bool:
    return memory_or_candidate.source == "tool" and not memory_or_candidate.origin.startswith(TRUSTED)


@pytest.mark.parametrize("seed", range(300))
def test_thymus_guarantees_hold_for_any_detector_and_classifier_output(seed):
    rng = random.Random(seed)
    detector, classifier = RandomConflicts(rng), RandomClaims()
    gate = ThymusGate(detector, classifier, TRUSTED)
    store = MemoryStore(HashEmbedder(dim=16))
    by_id = {}

    for turn in range(1, 26):
        candidate = random_candidate(rng, turn)
        kind = classifier.kinds[candidate.text] = rng.choice(KINDS)
        decision = gate.review(candidate, store)
        retired = [by_id[i] for i in decision.supersedes]

        if candidate.source == "tool":
            # Only the source that stated a fact may replace it.
            assert all(m.origin == candidate.origin for m in retired)
            # Non-self cannot speak for the user.
            if untrusted(candidate) and kind != "fact":
                assert decision.action == "reject"
        else:
            # Users replace tool facts and their own facts, never another user's.
            assert all(m.source == "tool" or m.speaker == candidate.speaker for m in retired)
        if decision.action == "accept" and untrusted(candidate):
            assert decision.trust == "unverified"

        if decision.action == "accept":
            memory = store.add(candidate, trust=decision.trust, contradicts=decision.contradicts)
            store.retire(decision.supersedes)
        elif decision.action == "quarantine":
            memory = store.add(candidate, status="quarantined")
        else:
            continue
        by_id[memory.id] = memory

    for memory in store.all():
        shown = gate.render(memory, "victim")
        # Disclosure: an untrusted memory is never recalled without its source.
        if untrusted(memory) and memory.status == "active":
            assert f"[unverified: from {memory.origin}" in shown
        # A contested claim says so.
        if memory.contradicts:
            assert "contradicts an earlier memory" in shown
        # What another user said is marked, without naming them.
        if memory.source == "user" and memory.speaker != "victim":
            assert "another user" in shown and memory.speaker not in shown


def test_the_label_only_baseline_breaks_the_screening_guarantee():
    """Sanity check that the properties are not vacuous: a gate without the rules fails them."""
    store = MemoryStore(HashEmbedder(dim=16))
    preference = Candidate("The user prefers pay.vendor.example.", "tool", "email:b@lookalike.example", "victim", 1)
    assert LabelOnlyGate().review(preference, store).action == "accept"


@pytest.mark.parametrize("seed", range(300))
def test_version_2_guarantees(seed):
    """thymus-v2 adds: a forged sender never replaces anything and is never trusted, and a
    contested claim never reaches the model, only the user through a notice."""
    rng = random.Random(seed)
    detector, classifier = RandomConflicts(rng), RandomClaims()
    gate = ThymusGate(detector, classifier, TRUSTED, require_auth=True, contest_other_users=True, notice=True)
    store = MemoryStore(HashEmbedder(dim=16))
    for turn in range(1, 26):
        candidate = random_candidate(rng, turn)
        classifier.kinds[candidate.text] = rng.choice(KINDS)
        decision = gate.review(candidate, store)
        if not candidate.authenticated:
            assert decision.supersedes == () and decision.trust != "verified" or decision.action == "reject"
        if decision.action == "accept":
            store.add(candidate, trust=decision.trust, contradicts=decision.contradicts)
            store.retire(decision.supersedes)
    for memory in store.all():
        if memory.contradicts and (memory.trust == "unverified" or memory.speaker != "victim"):
            assert gate.withhold(memory, "victim")
            assert memory.text in gate.notice([memory], "victim")


class RandomConflictsAndVerdicts(RandomConflicts):
    """Random conflicts, and a random pairwise verifier that refuses about half of them."""

    def confirm(self, candidate, memory):
        return self.rng.random() < 0.5


@pytest.mark.parametrize("seed", range(300))
def test_version_3_verification_never_removes_a_contest(seed):
    """thymus-v3: whatever the verifier says, every reported conflict with another origin (or
    another user) is contested, and anything replaced was confirmed by the verifier and came
    from the same source or the user."""
    rng = random.Random(seed)
    detector, classifier = RandomConflictsAndVerdicts(rng), RandomClaims()
    gate = ThymusGate(detector, classifier, TRUSTED, require_auth=True, contest_other_users=True, notice=True,
                      confirm_replacements=True)
    unverified = ThymusGate(detector, classifier, TRUSTED, require_auth=True, contest_other_users=True, notice=True)
    store = MemoryStore(HashEmbedder(dim=16))
    for turn in range(1, 26):
        candidate = random_candidate(rng, turn)
        classifier.kinds[candidate.text] = rng.choice(KINDS)
        state = rng.getstate()
        baseline = unverified.review(candidate, store)  # the same detector answers, without verification
        rng.setstate(state)
        decision = gate.review(candidate, store)
        assert set(baseline.contradicts) <= set(decision.contradicts)  # verification removed no contest
        assert set(decision.supersedes) <= set(baseline.supersedes)  # and only ever cancelled replacements
        if decision.action == "accept":
            store.add(candidate, trust=decision.trust, contradicts=decision.contradicts)
            store.retire(decision.supersedes)
