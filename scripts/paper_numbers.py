"""Write every result number the paper uses, from saved results.

Usage: uv run python scripts/paper_numbers.py
Writes paper/numbers-auto.tex (one macro per number; \\fooNum is the bare number for plots)
and paper/tables/full.tex (rates with 95% family-bootstrap intervals, and exact McNemar tests
of the final gate against every baseline). Nothing in the paper's result sections is typed by
hand except the prose around these macros.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

from thymus.harness import contains_any
from thymus.report import bootstrap_ci, dev_entries, in_dev, load, mcnemar_p
from thymus.scenarios import load_scenarios

K = Path("results/kaggle")
FINAL = "thymus-v2-verified"
DEV = dev_entries(Path("eval/dev_set.txt"))
SCENARIOS = {s.id: s for d in (Path("scenarios"), Path("scenarios-real")) for s in load_scenarios(d)}
BENCH = {
    "Qwen": [K / "qwen3-4b/results", K / "final-qwen3/results/qwen3-4b"],
    "Llama": [K / "llama3.1-8b/results", K / "llama-followup/results/llama3.1-8b", K / "llama-auto/results/llama3.1-8b",
              K / "final-llama/results/llama3.1-8b"],
}
BASELINES = ["allow-all", "user-only", "conflict-quarantine", "last-write-wins", "bounded-occupancy", "label-only", "thymus"]
NAMES = {"thymus": "thymus v1", "thymus-v2-auto": "thymus, no verification", "thymus-v2": "thymus, no verification",
         FINAL: "thymus (final)"}

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


def update_reaches(r):
    return (r["passed"] or bool(r.get("update_in_notice"))) if r["category"] == "update" else None


def recalled(r):
    return r["passed"] if r["category"] == "benign" else None


def recall_reaches(r):
    if r["category"] != "benign":
        return None
    s = SCENARIOS.get(r["scenario_id"])
    return r["passed"] or bool(s and r.get("notice") and contains_any(r["notice"], s.expect_any))


def by_gate(rows: list[dict], gate: str) -> list[dict]:
    return [r for r in rows if r["gate"] == gate]


def bench() -> list[str]:
    lines = []
    for model, paths in BENCH.items():
        rows = test_rows(paths)
        if not rows:
            continue
        put(f"abs{model}All", rate(by_gate(rows, "allow-all"), fooled))
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
        lines.append(full_table(model, rows))
    return lines


def ci_cell(rows: list[dict], metric) -> str:
    v = rate(rows, metric)
    if v is None:
        return "--"
    ci = bootstrap_ci(rows, metric)
    return f"{100 * v:.0f} [{100 * ci[0]:.0f}, {100 * ci[1]:.0f}]" if ci else f"{100 * v:.0f}"


def full_table(model: str, rows: list[dict]) -> str:
    title = {"Qwen": "qwen3-4B", "Llama": "Llama 3.1 8B"}[model]
    # Without verification: v2-auto, or v2 where auto was not run (identical on single claims).
    unverified = "thymus-v2-auto" if by_gate(rows, "thymus-v2-auto") else "thymus-v2"
    gates = [g for g in BASELINES + [unverified, FINAL] if by_gate(rows, g)]
    out = [f"\\paragraph{{{title}, test split.}} Rates in \\% with 95\\% family-bootstrap intervals; "
           "the last three columns compare the final gate with each defence on the same scenarios "
           "(discordant pairs final better / worse, exact McNemar $p$, attack success).", "",
           "\\begin{center}\\scriptsize\\begin{tabular}{@{}lccccc@{}}\\toprule",
           "Defence & Fooled & Updates & Recall & better/worse & $p$ \\\\ \\midrule"]
    mine = {r["scenario_id"]: r for r in by_gate(rows, FINAL)}
    for g in gates:
        rs = by_gate(rows, g)
        if g == FINAL:
            paired = "--", "--"
        else:
            theirs = {r["scenario_id"]: r for r in rs}
            pairs = [(bool(theirs[k]["poison_used"]), bool(mine[k]["poison_used"])) for k in mine.keys() & theirs.keys()
                     if mine[k]["category"] == "attack" and mine[k]["poison_used"] is not None
                     and theirs[k]["poison_used"] is not None]
            better = sum(1 for b, t in pairs if b and not t)
            worse = sum(1 for b, t in pairs if t and not b)
            p = mcnemar_p(worse, better)
            paired = f"{better}/{worse}", ("$<$0.001" if p < 0.001 else f"{p:.3f}")
        out.append(f"{NAMES.get(g, g)} & {ci_cell(rs, fooled)} & {ci_cell(rs, updated)} & "
                   f"{ci_cell(rs, recalled)} & {paired[0]} & {paired[1]} \\\\")
    out += ["\\bottomrule\\end{tabular}\\end{center}", ""]
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
    out = ["\\begin{table}[t]\\centering\\scriptsize",
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
    out += ["\\bottomrule\\end{tabular}\\end{table}", ""]
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


def main() -> None:
    tables = bench()
    real()
    longmemeval()
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
