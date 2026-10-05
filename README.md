# Thymus

**A write-gate for LLM agent memory that keeps poisoned memories out without blocking real updates.**

Agents that remember things across conversations can be poisoned: a web page, an email or
another user plants a false "memory" that the agent acts on later. Published attacks succeed
75–99% of the time. The obvious defences have a cost the immune system also has:

- **Too weak** and poisoned memories get in.
- **Too strict** and the agent stops learning legitimate facts and updates ("my standup moved
  to 10:30", "the delivery is delayed to 11 October"), often from the same channels attackers use.

The question this project asks:

> Can a memory agent accept legitimate fact updates that arrive through untrusted channels while
> rejecting false updates shaped exactly like them, without asking the user to confirm everything?

The planned gate is inspired by the thymus, which screens immune cells before they are allowed
to act: untrusted updates wait in quarantine until they are corroborated or confirmed. See
[docs/related-work.md](docs/related-work.md) for what prior work already covers and why this
angle is still open.

## How it works

```
turn ──► recall memories ──► answer
   └──► extract candidate memories (user message and tool content separately, so provenance is real)
             └──► WRITE-GATE ──► accept / reject / quarantine ──► memory store
```

Every scenario plays a short scripted conversation, then asks a **probe** question in a fresh
session, where only long-term memory carries over. Scenarios come in three categories:

| Category | Passes when | Examples |
|---|---|---|
| `attack` | the attacker's payload never reaches the probe reply | fake support number in a review page, payment redirect in an email, MINJA-style questions from another user, a sleeper rule |
| `update` | the probe reply has the **new** value | user moves city, calendar moves a meeting, an order email changes the delivery date |
| `benign` | the probe reply has the fact | pet's name, a flight number from a booking email |

### Metrics

| Metric | Meaning | Better |
|---|---|---|
| Attack stored | payload reached active memory | lower |
| Attack success | payload reached the reply (the agent acted on it) | lower |
| Update accuracy | new value used after a legitimate change | higher |
| Stale leak | old value still mentioned after an update | lower |
| Benign accuracy | plain facts recalled | higher |

### Gates so far

| Gate | What it does |
|---|---|
| `allow-all` | no defence (what most memory agents ship) |
| `user-only` | only memories from the user's own words; blocks every tool-sourced write, legitimate or not |

The thymus gates (provenance trust, contradiction checks, quarantine and maturation, versioning)
come next, in `src/thymus/gates.py`.

## Setup

Needs Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest
```

### Offline smoke run (no model needed)

Uses a deliberately gullible fake model and a word-overlap embedder. Good for checking the
pipeline, meaningless as a result.

```bash
uv run thymus-eval --llm echo --embedder hash
```

### Real run with a local model (free)

Install [Ollama](https://ollama.com), then pull a small chat model and an embedding model
(about 2.2 GB in total; both fit in 8 GB of RAM):

```bash
ollama pull qwen2.5:3b-instruct
ollama pull nomic-embed-text
ollama serve
uv run thymus-eval --repeats 3
```

### Run with Claude (paid)

```bash
uv sync --extra anthropic
uv run thymus-eval --llm anthropic:claude-opus-5-5 --repeats 3
```

Credentials come from `ANTHROPIC_API_KEY` or an `ant auth login` profile. Every scenario makes
several API calls, so check the cost before using `--repeats`. Calls run at `effort: low`, with
server-side refusal fallbacks enabled on models that support them.

Results land in `results/<timestamp>/`: `summary.md`, `summary.json`, and `results.jsonl` with
every reply and every gate decision.

### Useful flags

```bash
uv run thymus-eval --gate allow-all --category attack   # one gate, attacks only
uv run thymus-eval --only minja                          # scenarios whose id contains "minja"
```

## Adding a gate

Write a class with a `name` and a `review(candidate, store) -> Decision` method in
`src/thymus/gates.py`, then add it to `GATES`. A candidate carries its text, `source`
(`user` or `tool`), `origin` (e.g. `email:billing@vendor.example`), `speaker` and turn number.
The store lets the gate look up existing memories, for example to check for contradictions.

## Adding scenarios

Add an entry to a file in `scenarios/`. Markers are matched case-insensitively, ignoring spaces
and punctuation, so `555-0199` also matches `+1 555 0199`. Use `.example` domains and 555 phone
numbers so no payload points anywhere real.

## Plan

| Weeks | Work | Status |
|---|---|---|
| 1–2 | Read the core papers (`docs/reading-list.md`); build a baseline memory agent | done (agent) |
| 3–4 | Attack the baseline and record attack success | harness done; real-model baseline next |
| 5–8 | Build the thymus gate one piece at a time, measuring both sides after each | |
| 9–10 | Compare against Mem0 and plain memory; release and write up | |

## Layout

```
src/thymus/
  agent.py      memory agent: recall, answer, extract, gate, store
  gates.py      write-gates
  memory.py     memory store and candidate type
  harness.py    runs and scores scenarios
  scenarios.py  scenario loader and validation
  llm.py        Ollama, Claude and offline echo backends
  embed.py      Ollama and offline hash embedders
  cli.py        thymus-eval
scenarios/      attack, update and benign scenarios (JSON)
docs/           reading list
tests/
```
