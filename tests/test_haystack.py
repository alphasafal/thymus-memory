from pathlib import Path

from thymus.cli import main
from thymus.embed import HashEmbedder
from thymus.gates import AllowAllGate, ThymusGate, UserOnlyGate
from thymus.haystack import background_pool, fill
from thymus.memory import MemoryStore

SCENARIOS = Path(__file__).parent.parent / "scenarios"
POOL = background_pool(SCENARIOS)


class NoCalls:
    """The haystack must never ask a gate's model anything."""

    def find(self, candidate, store):
        raise AssertionError("conflict detector called")

    def kind(self, text):
        raise AssertionError("classifier called")


def test_pool_has_one_fact_per_family_with_its_provenance():
    assert len(POOL) == 90 and len({f.family for f in POOL}) == 90
    sources = {f.source for f in POOL}
    assert sources == {"user", "tool"}
    assert all(f.origin == "chat" for f in POOL if f.source == "user")


def test_fill_is_deterministic_per_family_and_skips_the_scenarios_own_family():
    a, b = MemoryStore(HashEmbedder()), MemoryStore(HashEmbedder())
    fill(a, AllowAllGate(), "standup-time--attack", POOL, 30)
    fill(b, AllowAllGate(), "standup-time--legit", POOL, 30)
    assert [m.text for m in a.all()] == [m.text for m in b.all()] and len(a.all()) == 30
    standup = next(f.text for f in POOL if f.family == "standup-time")
    assert standup not in {m.text for m in a.all()}
    assert all(m.created_at == 0 for m in a.all())


def test_each_gate_admits_background_facts_as_it_would_without_model_calls():
    thymus = ThymusGate(NoCalls(), NoCalls())
    stores = {}
    for name, gate in {"allow": AllowAllGate(), "user-only": UserOnlyGate(), "thymus": thymus}.items():
        stores[name] = MemoryStore(HashEmbedder())
        fill(stores[name], gate, "sip-date--attack", POOL, 40)
    assert len(stores["allow"].all()) == 40
    assert 0 < len(stores["user-only"].all()) < 40
    assert all(m.source == "user" for m in stores["user-only"].all())
    for m in stores["thymus"].all():
        expected = "verified" if m.source == "user" or m.origin.startswith("calendar:") else "unverified"
        assert m.trust == expected


def test_cli_runs_with_a_haystack(tmp_path):
    out = tmp_path / "out"
    code = main(["--llm", "echo", "--embedder", "hash", "--only", "standup-time--", "--haystack", "20",
                 "--gate", "thymus", "--out", str(out), "--no-cache"])
    assert code == 0
    meta = next(out.rglob("meta.json")).read_text()
    assert '"haystack": 20' in meta
