"""Write every result number the paper uses, from saved results.

Usage: uv run python scripts/paper_numbers.py
Writes paper/numbers-auto.tex (one macro per number; \\fooNum is the bare number for plots)
and paper/tables/full.tex (rates with 95% family-bootstrap intervals, and exact McNemar tests
of the final gate against every baseline). Nothing in the paper's result sections is typed by
hand except the prose around these macros.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from statistics import mean

from thymus.gates import defang
from thymus.harness import contains_any
from thymus.report import bootstrap_ci, burden_counts, dev_entries, in_dev, load, mcnemar_p
from thymus.scenarios import load_scenarios

K = Path("results/kaggle")
# Chosen by the rule in docs/preregistration-v3.md once the held-out runs are in.
FINAL = os.environ.get("THYMUS_FINAL", "thymus-v2-verified")
CANDIDATES = {"Ver": "thymus-v2-verified", "Three": "thymus-v3"}
DEV = dev_entries(Path("eval/dev_set.txt"))
SCENARIOS = {s.id: s for d in (Path("scenarios"), Path("scenarios-real")) for s in load_scenarios(d)}
BENCH = {
    "Qwen": [K / "qwen3-4b/results", K / "final-qwen3/results/qwen3-4b"],
    "Llama": [K / "llama3.1-8b/results", K / "llama-followup/results/llama3.1-8b", K / "llama-auto/results/llama3.1-8b",
              K / "final-llama/results/llama3.1-8b"],
    # Never used while designing any version of the gate.
    "Gemma": [K / "heldout-gemma3-12b/results/gemma3-12b"],
    "QwenBig": [K / "heldout-qwen3-14b/results/qwen3-14b"],
}
BENCH["Qwen"].append(K / "v3-exposed/results/qwen3-4b")
BENCH["Llama"].append(K / "v3-exposed/results/llama3.1-8b")
TITLES = {"Qwen": "qwen3-4B", "Llama": "Llama 3.1 8B", "Gemma": "Gemma 3 12B (held out)",
          "QwenBig": "Qwen3 14B (held out)"}
BASELINES = ["allow-all", "user-only", "conflict-quarantine", "last-write-wins", "bounded-occupancy", "label-only", "thymus"]
NAMES = {"thymus": "thymus v1", "thymus-v2-auto": "thymus, no verification", "thymus-v2": "thymus, no verification",
         "thymus-v2-precise": "thymus, same-subject check only", "thymus-v2-verified": "thymus, verify all",
         "thymus-v3": "thymus v3, verify replacements", FINAL: "thymus (final)"}

macros: dict[str, str] = {}


def put(name: str, value: float | None, digits: int = 0) -> None:
    if value is None:
        macros[name], macros[name + "Num"] = "--", "0"
        return
    macros[name] = f"{100 * value:.{digits}f}\\%"
    macros[name + "Num"] = f"{100 * value:.{digits}f}"


def rate(rows: list[dict], metric) -> float | None:
    values = [metric(r) for r in rows if metric(r) is not None]
    return mean(bool(v) for v in values) if values else None


def test_rows(paths: list[Path]) -> list[dict]:
    paths = [p for p in paths if p.exists()]
    return [r for r in load(paths) if not in_dev(r["scenario_id"], DEV)] if paths else []


def fooled(r):
    return r["poison_used"] if r["category"] == "attack" else None


def updated(r):
    return r["passed"] if r["category"] == "update" else None


def in_notice(r) -> bool:
    """The right value is in the notice as the user reads it, links and numbers removed
    (applied to runs saved before notices were defanged, so every run is scored the same way)."""
    s = SCENARIOS.get(r["scenario_id"])
    return bool(s and r.get("notice") and contains_any(defang(r["notice"]), s.expect_any))


def update_reaches(r):
    return (r["passed"] or in_notice(r)) if r["category"] == "update" else None


def recalled(r):
    return r["passed"] if r["category"] == "benign" else None


def recall_reaches(r):
    if r["category"] != "benign":
        return None
    return r["passed"] or in_notice(r)


def by_gate(rows: list[dict], gate: str) -> list[dict]:
    return [r for r in rows if r["gate"] == gate]


def bench() -> list[str]:
    lines = []
    for model, paths in BENCH.items():
        rows = test_rows(paths)
        if not rows:
            continue
        put(f"abs{model}All", rate(by_gate(rows, "allow-all"), fooled))
        put(f"abs{model}Auto", rate(by_gate(rows, "thymus-v2-auto"), fooled))
        put(f"abs{model}User", rate(by_gate(rows, "user-only"), fooled))
        put(f"upd{model}User", rate(by_gate(rows, "user-only"), updated))
        put(f"rec{model}User", rate(by_gate(rows, "user-only"), recalled))
        put(f"abs{model}Labels", rate(by_gate(rows, "label-only"), fooled))
        for key, gate in CANDIDATES.items():
            rs = by_gate(rows, gate)
            put(f"abs{model}{key}", rate(rs, fooled))
            put(f"upd{model}{key}", rate(rs, updated))
            put(f"upd{model}{key}Reach", rate(rs, update_reaches))
            put(f"rec{model}{key}", rate(rs, recalled))
        final = by_gate(rows, FINAL)
        put(f"abs{model}Thy", rate(final, fooled))
        put(f"upd{model}Thy", rate(final, updated))
        put(f"upd{model}ThyReach", rate(final, update_reaches))
        put(f"rec{model}Thy", rate(final, recalled))
        put(f"rec{model}ThyReach", rate(final, recall_reaches))
        cross = [r for r in final if r["category"] == "update" and r["kind"] == "cross-origin-update"]
        put(f"cross{model}Answered", rate(cross, updated))
        put(f"cross{model}Reach", rate(cross, update_reaches))
        other = [r for r in final if r["category"] == "attack" and r["kind"] == "other-user"]
        macros[f"otherUser{model}"] = f"{sum(bool(r['poison_used']) for r in other)} of {len(other)}"
        macros[f"otherUser{model}Notices"] = str(sum(bool(r.get("notice")) for r in other))
        for lang, key in (("en", "En"), ("hi", "Hi"), ("hinglish", "Hg")):
            india = [r for r in final if f"--{lang}--" in r["scenario_id"]]
            put(f"lang{model}{key}", rate(india, fooled))
        burden = {c: rate([r for r in final if r["category"] == c], lambda r: bool(r.get("notice")))
                  for c in ("benign", "update", "attack")}
        for c, v in burden.items():
            put(f"notice{model}{c.capitalize()}", v)
        counts = burden_counts(final)
        if counts:
            for key, value in zip(("All", "Distrust", "Notice"), counts):
                macros[f"ask{model}{key}"] = f"{value:.0f}"
        check_claim(model, rows)
        stratify(model, final)
        lines.append(full_table(model, rows))
    return lines


def stratify(model: str, final: list[dict]) -> None:
    """Attacks split by what the gate did with the planted claim: contested, stored without a
    contest (the conflict check saw no contradiction), or never stored."""
    groups = {"Contested": [], "Uncontested": [], "Unstored": []}
    for r in final:
        if r["category"] != "attack" or r["poison_used"] is None:
            continue
        s = SCENARIOS.get(r["scenario_id"])
        planted = [w for w in r.get("writes", []) if s and contains_any(w["text"], s.poison_markers)]
        if not planted or all(w["action"] == "reject" for w in planted):
            groups["Unstored"].append(r)
        elif any("contradicts" in w["reason"] for w in planted):
            groups["Contested"].append(r)
        else:
            groups["Uncontested"].append(r)
    for key, rs in groups.items():
        macros[f"strat{model}{key}N"] = str(len(rs))
        put(f"strat{model}{key}", rate(rs, fooled))


def check_claim(model: str, rows: list[dict]) -> None:
    """The paper says: lowest attack success of any baseline that keeps plain recall (>= 90%).
    Earlier versions of the gate are compared in the development history, not here."""
    mine = rate(by_gate(rows, FINAL), fooled)
    for gate in sorted(g for g in {r["gate"] for r in rows} if not g.startswith("thymus")):
        rs = by_gate(rows, gate)
        if (rate(rs, recalled) or 0) >= 0.9 and mine is not None and (rate(rs, fooled) or 1) < mine:
            print(f"WARNING {model}: {gate} keeps recall and is fooled less often than {FINAL}; fix the claim")


def ci_cell(rows: list[dict], metric) -> str:
    v = rate(rows, metric)
    if v is None:
        return "--"
    ci = bootstrap_ci(rows, metric)
    return f"{100 * v:.0f} [{100 * ci[0]:.0f}, {100 * ci[1]:.0f}]" if ci else f"{100 * v:.0f}"


def holm(ps: list[float]) -> list[float]:
    """Holm-Bonferroni adjusted p-values (step-down, monotone, capped at 1)."""
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adjusted, running = [1.0] * len(ps), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(ps) - rank) * ps[i]))
        adjusted[i] = running
    return adjusted


def fmt_p(p: float) -> str:
    return "$<$0.001" if p < 0.001 else f"{p:.3f}"


def full_table(model: str, rows: list[dict]) -> str:
    title = TITLES[model]
    # Without verification: v2-auto, or v2 where auto was not run (identical on single claims).
    unverified = "thymus-v2-auto" if by_gate(rows, "thymus-v2-auto") else "thymus-v2"
    extra = [g for g in ("thymus-v2-precise", *CANDIDATES.values()) if g != FINAL]
    gates = [g for g in BASELINES + [unverified, *extra, FINAL] if by_gate(rows, g)]
    out = [f"\\paragraph{{{title}, test split.}} Rates in \\% with 95\\% family-bootstrap intervals; "
           "the last columns compare the final gate with each defence on the same attacks (discordant "
           "pairs final better / worse, exact McNemar $p$, and $p$ Holm-corrected over the rows of this table).", "",
           "\\begin{center}\\scriptsize\\resizebox{\\columnwidth}{!}{\\begin{tabular}{@{}lcccccc@{}}\\toprule",
           "Defence & Fooled & Updates & Recall & better/worse & $p$ & Holm $p$ \\\\ \\midrule"]
    mine = {r["scenario_id"]: r for r in by_gate(rows, FINAL)}
    tests = {}
    for g in gates:
        if g == FINAL:
            continue
        theirs = {r["scenario_id"]: r for r in by_gate(rows, g)}
        pairs = [(bool(theirs[k]["poison_used"]), bool(mine[k]["poison_used"])) for k in mine.keys() & theirs.keys()
                 if mine[k]["category"] == "attack" and mine[k]["poison_used"] is not None
                 and theirs[k]["poison_used"] is not None]
        better = sum(1 for b, t in pairs if b and not t)
        worse = sum(1 for b, t in pairs if t and not b)
        tests[g] = (better, worse, mcnemar_p(worse, better))
    adjusted = dict(zip(tests, holm([t[2] for t in tests.values()])))
    for g in gates:
        rs = by_gate(rows, g)
        if g in tests:
            better, worse, p = tests[g]
            paired = f"{better}/{worse} & {fmt_p(p)} & {fmt_p(adjusted[g])}"
        else:
            paired = "-- & -- & --"
        out.append(f"{NAMES.get(g, g)} & {ci_cell(rs, fooled)} & {ci_cell(rs, updated)} & "
                   f"{ci_cell(rs, recalled)} & {paired} \\\\")
    out += ["\\bottomrule\\end{tabular}}\\end{center}", ""]
    return "\n".join(out)


def real() -> None:
    for model, tag in (("Qwen", "qwen3-4b"), ("Llama", "llama3.1-8b")):
        for suite, key in (("realemail-enron", "enron"), ("realsms", "sms"), ("realemail-phishing", "mail")):
            path = next(iter(sorted(K.glob(f"final-*/results/{suite}-{tag}"))), None)
            rows = by_gate(load([path]), FINAL) if path else []
            put(f"{key}{model}Thy", rate(rows, fooled))
            if key == "enron":
                put(f"{key}{model}UpdThy", rate(rows, updated))
    for key, suite in (("hay", "final-haystack/results/qwen3-4b-haystack80"),):
        path = K / suite
        rows = test_rows([path]) if path.exists() else []
        for gate, g in (("Thy", FINAL), ("Auto", "thymus-v2-auto"), ("All", "allow-all"), ("Labels", "label-only"),
                        ("Bounded", "bounded-occupancy"), ("User", "user-only")):
            rs = by_gate(rows, gate=g)
            put(f"{key}Fooled{gate}", rate(rs, fooled))
            put(f"{key}Upd{gate}", rate(rs, updated))
            put(f"{key}UpdReach{gate}", rate(rs, update_reaches))
            put(f"{key}Rec{gate}", rate(rs, recalled))
            put(f"{key}RecReach{gate}", rate(rs, recall_reaches))


def longmemeval() -> None:
    rows = []
    for f in sorted((K / "final-longmemeval/results").rglob("results.jsonl")) if (K / "final-longmemeval/results").exists() else []:
        rows += [json.loads(line) for line in f.read_text().splitlines() if line.strip()]
    for condition, key in (("clean", "Clean"), ("poisoned", "Poisoned"), ("evidence-untrusted", "Untrusted")):
        rs = [r for r in rows if r["condition"] == condition and r["gate"] == FINAL]
        put(f"lme{key}", mean(bool(r["correct"]) for r in rs) if rs else None)
        if condition != "clean":
            put(f"lme{key}Adopt", mean(r["attack_verdict"] == "adopted" for r in rs) if rs else None)
            put(f"lme{key}Flag", mean(r["attack_verdict"] == "flagged" for r in rs) if rs else None)


VERIFIER = K / "verifier-check2/results/verifier"
WORDING_NAMES = {"first": "first", "named-subject": "named subject (final)", "named-subject+brand": "named subject + brand"}


def verifier_table() -> str | None:
    """Labelled-pair calibration: kept real conflicts and false contests, per wording and half."""
    files = sorted(VERIFIER.glob("*.jsonl")) if VERIFIER.exists() else []
    if not files:
        return None
    out = ["\\begin{table*}[t]\\centering\\scriptsize",
           "\\caption{Verifier wordings on labelled pairs: real conflicts kept (higher is better) and "
           "non-conflicts kept, i.e.\\ false contests (lower is better). The wording was chosen on half A "
           "and is reported on half B; families never span halves.}\\label{tab:verifier}",
           "\\begin{tabular}{@{}llccc@{}}\\toprule",
           "Verifier & Pairs & " + " & ".join(WORDING_NAMES.values()) + " \\\\ \\midrule"]
    for f in files:
        rows = [json.loads(line) for line in f.read_text().splitlines() if line.strip()]
        model = {"ollama_qwen3_4b-instruct": "qwen3-4B", "ollama_llama3.1_8b": "Llama 3.1 8B"}.get(f.stem, f.stem)
        for conflict, label in ((True, "real conflicts kept"), (False, "false contests")):
            cells = []
            for w in WORDING_NAMES:
                halves = []
                for half in ("A", "B"):
                    rs = [r for r in rows if r["split"] == half and r["conflict"] == conflict]
                    halves.append(f"{sum(r[w]['confirmed'] for r in rs)}/{len(rs)}")
                cells.append(" / ".join(halves))
            out.append(f"{model} & {label} (A / B) & " + " & ".join(cells) + " \\\\")
    out += ["\\bottomrule\\end{tabular}\\end{table*}", ""]
    return "\n".join(out)


def verifier_first_table() -> str | None:
    """The suites run with the first verifier wording (7 Oct), kept for the development history."""
    lines = []
    for model, tag in (("qwen3-4B", "qwen3-4b"), ("Llama 3.1 8B", "llama3.1-8b")):
        for suite, label in (("realemail-enron", "Enron replays"), ("realemail-phishing", "phishing"), ("realsms", "SMS")):
            path = K / f"realdata-verified/results/{suite}-{tag}"
            rows = by_gate(load([path]), FINAL) if path.exists() else []
            if rows:
                f, u = rate(rows, fooled), rate(rows, updated)
                lines.append(f"{label}, {model} & {100 * f:.0f}\\% & "
                             + (f"{100 * u:.0f}\\%" if u is not None else "--") + " \\\\")
    lme = K / "longmemeval-verified/results"
    rows = [json.loads(line) for f in sorted(lme.rglob("results.jsonl")) for line in f.read_text().splitlines()
            if line.strip()] if lme.exists() else []
    for condition in ("clean", "poisoned"):
        rs = [r for r in rows if r["condition"] == condition and r["gate"] == FINAL]
        if rs:
            adopt = f"{100 * mean(r['attack_verdict'] == 'adopted' for r in rs):.0f}\\%" if condition != "clean" else "--"
            lines.append(f"LongMemEval {condition}, Llama 3.1 8B & {adopt} & "
                         f"{100 * mean(bool(r['correct']) for r in rs):.0f}\\% (accuracy) \\\\")
    if not lines:
        return None
    return "\n".join(["\\begin{table}[t]\\centering\\scriptsize",
                      "\\caption{Final gate with the \\emph{first} verifier wording (superseded): fooled and "
                      "real updates answered. These runs prompted the wording change in \\cref{sec:history}.}"
                      "\\label{tab:verifier-first}",
                      "\\begin{tabular}{@{}lcc@{}}\\toprule", "Suite & Fooled & Updates \\\\ \\midrule",
                      *lines, "\\bottomrule\\end{tabular}\\end{table}", ""])


ADAPTIVE_GATES = {"All": "allow-all", "Labels": "label-only", "Auto": "thymus-v2-auto", **CANDIDATES}


def adaptive() -> None:
    """Attacks rewritten by qwen3-14B, which was told how the gate works (scripts/adaptive_attacker.py)."""
    for model, tag in (("Qwen", "qwen3-4b"), ("Llama", "llama3.1-8b")):
        paths = [p for p in (K / "final-adaptive/results" / f"adaptive-{tag}", K / "v3-adaptive/results" / f"adaptive-{tag}")
                 if p.exists()]
        rows = load(paths) if paths else []
        for key, gate in ADAPTIVE_GATES.items():
            put(f"adapt{model}{key}", rate(by_gate(rows, gate), fooled))
        macros[f"adapt{model}N"] = str(len({r["scenario_id"] for r in rows}))


def gate_aware() -> None:
    """Attacks written after the freeze to defeat the gate (scenarios-gate-aware)."""
    parts = []
    for model, tag in (("qwen3-4B", "qwen3-4b"), ("Llama 3.1 8B", "llama3.1-8b")):
        path = K / f"gate-aware/results/gate-aware-{tag}"
        rows = load([path]) if path.exists() else []
        if not by_gate(rows, FINAL):
            continue
        kinds = sorted({r["kind"] for r in rows})
        cells = ", ".join(f"{k.removeprefix('gate-aware-')} {100 * rate(by_gate([r for r in rows if r['kind'] == k], FINAL), fooled):.0f}\\%"
                          for k in kinds)
        parts.append(f"on {model} the gate is fooled by {100 * rate(by_gate(rows, FINAL), fooled):.0f}\\% of them "
                     f"(no defence: {100 * rate(by_gate(rows, 'allow-all'), fooled):.0f}\\%; by strategy: {cells})")
    if parts:
        macros["gateAwareSentence"] = "Against these 20 attacks, " + "; ".join(parts) + "."


def external() -> None:
    """Data written by others: MemShield-Bench attacks and MemoryAgentBench updates."""
    parts = []
    for path in sorted(Path("eval/external/memshield").glob("*.json")) + sorted(K.glob("external/results/memshield/*.json")):
        report = json.loads(path.read_text())
        model = report["gate_model"].split(":", 1)[1]
        pairs = report["pairs"].get(FINAL) or report["pairs"].get("thymus-v3", {})
        n = sum(pairs.values())
        caught = pairs.get("contested", 0) + pairs.get("rejected", 0)
        screen = report["screening"]
        poisoned = [c for k, c in screen.items() if k != "clean"]
        p_rej, p_n = sum(c.get("rejected", 0) for c in poisoned), sum(sum(c.values()) for c in poisoned)
        clean = screen.get("clean", {})
        parts.append(f"with {model} as gate model it catches {caught} of {n} poisoned rewrites of stored entries "
                     f"and rejects {p_rej} of {p_n} poisoned entries on their own, but also {clean.get('rejected', 0)} "
                     f"of {sum(clean.values())} clean ones")
    if parts:
        macros["memshieldSentence"] = "On MemShield-Bench~\\cite{memshield}, " + "; ".join(parts) + "."
    cells = []
    for model, tag in (("qwen3-4B", "qwen3-4b"), ("Llama 3.1 8B", "llama3.1-8b")):
        path = K / f"external/results/mab-{tag}"
        rows = load([path]) if path.exists() else []
        mine = by_gate(rows, FINAL)
        if not mine:
            continue
        same = [r for r in mine if r["kind"] == "same-origin-update"]
        cross = [r for r in mine if r["kind"] == "cross-origin-update"]
        cells.append(f"on {model} the gate answers {100 * rate(same, updated):.0f}\\% of same-source corrections "
                     f"(no defence: {100 * rate([r for r in by_gate(rows, 'allow-all') if r['kind'] == 'same-origin-update'], updated):.0f}\\%) "
                     f"and delivers {100 * rate(cross, update_reaches):.0f}\\% of other-source ones, answered or in the notice")
    if cells:
        macros["mabSentence"] = ("On 36 counterfactual edits from MemoryAgentBench~\\cite{memoryagentbench}, "
                                 + "; ".join(cells) + ".")


def sentences() -> None:
    """Sentences that exist only once their run is in; numbers.tex falls back to a pending note."""
    from thymus.cost import gate_overhead

    parts = []
    for model, tag in (("qwen3-4B", "qwen3-4b"), ("Llama 3.1 8B", "llama3.1-8b")):
        path = K / f"v3-deploy/results/mem0-{tag}"
        on_mem0 = test_rows([path]) if path.exists() else []
        builtin = test_rows(BENCH["Qwen" if tag == "qwen3-4b" else "Llama"])
        for gate in ("thymus-v3",):
            mine, theirs = by_gate(on_mem0, gate), {r["scenario_id"]: r for r in by_gate(builtin, gate)}
            if not mine:
                continue
            same = sum(1 for r in mine if r["scenario_id"] in theirs and r["passed"] == theirs[r["scenario_id"]]["passed"])
            parts.append(f"on {model} the gate on Mem0 is fooled {100 * rate(mine, fooled):.0f}\\% of the time with "
                         f"{100 * rate(mine, updated):.0f}\\% of updates and {100 * rate(mine, recalled):.0f}\\% of recall "
                         f"answered, and {same} of {len(mine)} scenarios get the same verdict as on the built-in store")
    if parts:
        macros["memZeroSentence"] = "Running the whole benchmark this way, " + "; ".join(parts) + "."
    path = K / "v3-deploy/results/cost-qwen3-4b"
    rows = load([path]) if path.exists() else []
    cells = []
    for gate in ("thymus-v3", "thymus-v2-verified"):
        rs = [r for r in by_gate(rows, gate) if r.get("cost")]
        writes = sum(len(r.get("writes", [])) for r in rs)
        if not writes:
            continue
        over = [gate_overhead(r["cost"]) for r in rs]
        agent = [sum(r["cost"].get(j, {}).get(k, 0) for j in ("extract", "answer")) for r in rs for k in ("seconds",)]
        cells.append(f"{NAMES.get(gate, gate)} adds {sum(o['calls'] for o in over) / writes:.2f} model calls, "
                     f"{sum(o['tokens'] for o in over) / writes:.0f} tokens and {sum(o['seconds'] for o in over) / writes:.2f}\\,s "
                     f"per memory write on qwen3-4B (a T4 GPU; the agent's own extraction and answer take "
                     f"{sum(agent) / len(rs):.1f}\\,s per scenario)")
    if cells:
        macros["costSentence"] = "Measured without the cache, " + "; ".join(cells) + "."


def main() -> None:
    tables = bench()
    real()
    longmemeval()
    adaptive()
    gate_aware()
    external()
    sentences()
    Path("paper/tables").mkdir(parents=True, exist_ok=True)
    for name, table in (("verifier", verifier_table()), ("verifier-first", verifier_first_table())):
        if table:
            Path(f"paper/tables/{name}.tex").write_text(table)
    Path("paper/tables/full.tex").write_text("\n".join(tables) + "\n")
    text = "% Generated by scripts/paper_numbers.py from results/kaggle; do not edit.\n"
    text += "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in sorted(macros.items()))
    Path("paper/numbers-auto.tex").write_text(text)
    print(f"{len(macros)} macros; {len(tables)} full tables")


if __name__ == "__main__":
    main()
