# shortstoryfun

Private, single-user tool that turns a raw idea into a **strong short-story draft** (~2,000–7,500 words) for **you** to rewrite and own.

It is not a product, not multi-user, and not a publishing platform. Output is always a **raw draft**, never finished literature.

---

## What this tool does

You write a spark. The tool helps you shape a premise and outline (you approve both). Then it drafts prose in chunks, assembles a continuous short story you can print, and logs every model call for cost and authorship provenance.

```text
Spark  →  Premise (you approve)  →  Outline (you approve)  →  Draft  →  Assemble / Print
                ↑ stop here if unhappy              ↑ nothing drafts until you say so
```

**Important design notes**

- **Checkpoints:** No prose is drafted until you approve the premise *and* the outline.
- **Scenes are scaffolding:** Internally the outline/draft use scene beats so each model call stays focused and cheap. The file you print (`print.md`) is **continuous short-story prose** — not a screenplay.
- **You own the rewrite:** Print it, mark it up, make it yours. Use `diff` later to see how much you changed.

---

## Setup (once)

### 1. OpenRouter key (required)

1. Create a key at [openrouter.ai/keys](https://openrouter.ai/keys).
2. **Set a spending limit** on the key (recommended).
3. You will paste it into `.env` below. Never commit `.env`.

### 2. Install

Python 3.10+ recommended (3.9 works).

```bash
cd shortstory   # or wherever you cloned the repo
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure `.env`

```bash
cp .env.example .env
```

Edit `.env`:

```bash
OPENROUTER_API_KEY=sk-or-v1-...   # your real key

# Recommended for reliable prose (fewer empty replies from "thinking" models)
DRAFT_MODEL=deepseek/deepseek-v4.1-flash

# Optional alternatives
# DRAFT_MODEL=qwen/qwen3.8-27b

PREMIUM_MODEL=moonshotai/kimi-k3.1-pro
LLM_TEMPERATURE=0.7
BUDGET_CAP_USD=1.00

HOST=127.0.0.1
PORT=5001          # use 5001 if macOS already occupies 5000 (AirPlay Receiver)
```

### 4. Style bible (recommended)

Edit `style.yaml`:

- POV, tense, tone, rhythm
- Banned phrases / em-dash ban
- **`voice_references`:** short paragraphs from **your own writing only** (never living authors or franchises)

---

## How to run a story (CLI — recommended)

Commands live on `python shortstory.py`. Replace `my-slug` with your story folder name.

### Step 1 — Spark (your words)

```bash
python shortstory.py spark "Your raw idea here…" --slug my-slug
```

Creates `stories/my-slug/` and saves `00_spark.md`.  
Sparks that name living authors or franchises are rejected.

### Step 2 — Premise (3 options)

```bash
python shortstory.py premise my-slug
```

Writes `01_premise.md` with three options (protagonist, want, need, flaw, setting, conflict, stakes, ending turn).

**You:** open the file, pick one option (or rewrite it), save.

```bash
python shortstory.py approve-premise my-slug
```

### Step 3 — Outline (6–12 beats)

```bash
python shortstory.py frameworks          # list structures
python shortstory.py outline my-slug --framework try_fail --words 5000
```

Frameworks: `story_circle` | `try_fail` | `mice`

Writes `02_outline.md`. Edit freely, then:

```bash
python shortstory.py approve-outline my-slug
```

Until this is approved, **draft is locked**.

### Step 4 — Draft prose

```bash
python shortstory.py draft my-slug
```

One model call per outline beat → `scenes/01.md`, `02.md`, …

Redraft a single weak section:

```bash
python shortstory.py redraft my-slug 5
```

Optional stronger model (manual only — never automatic):

```bash
python shortstory.py draft my-slug --premium
python shortstory.py redraft my-slug 8 --premium
```

### Step 5 — Continuity (optional)

```bash
python shortstory.py continuity my-slug
```

Reports name/timeline contradictions; **does not auto-rewrite**.

### Step 6 — Assemble + print

```bash
python shortstory.py assemble my-slug
```

Produces:

| File | Purpose |
|------|---------|
| `draft_v1.md` | Working draft + word-count report |
| **`print.md`** | **Clean continuous story for printing / rewriting** |

### Step 7 — Cost, provenance, export

```bash
python shortstory.py cost my-slug      # $ by stage + story total
python shortstory.py diff my-slug      # how much of model text you changed
python shortstory.py export my-slug --format pdf   # md|txt|docx|pdf|epub
python shortstory.py list
```

---

## Minimal local web UI

```bash
source venv/bin/activate
python webapp.py
# open http://127.0.0.1:5001   (or whatever PORT is in .env)
```

Same pipeline as the CLI: Save spark → Premise ×3 → Approve premise → Outline → Approve outline → Draft scenes → Assemble → Cost report.

Check the **slug** field when continuing a story (e.g. `working-title-the-heron`).

---

## Story folder layout

Everything for one story lives in one folder (edit any file by hand and resume):

```text
stories/<slug>/
  00_spark.md          # your raw idea
  01_premise.md        # 3 options — edit, then approve
  02_outline.md        # scene beats — edit, then approve
  scenes/
    01.md …            # internal draft chunks (scaffolding)
  03_continuity.md     # continuity notes (if generated)
  draft_v1.md          # assembled draft + word counts
  print.md             # clean continuous prose for print/rewrite
  provenance.jsonl     # every model call (authorship log)
  costs.jsonl          # tokens + $ per call
  meta.yaml            # approvals, target words, status
```

`stories/` is gitignored. Each new story can also get its own mini git history for edit tracking.

---

## Models and cost

| Env var | Typical value | When used |
|---------|---------------|-----------|
| `DRAFT_MODEL` | `deepseek/deepseek-v4.1-flash` (recommended) | Default for all stages |
| | `qwen/qwen3.8-27b` | Alternative volume tier |
| `PREMIUM_MODEL` | `moonshotai/kimi-k3.1-pro` | Only with `--premium` / UI checkbox |
| `BUDGET_CAP_USD` | e.g. `1.00` | Stops a run before exceeding |

- Prices for estimates: `config/model_prices.yaml`
- A full ~5k-word draft is usually **cents**, not dollars, on the cheap tier
- Models run on **OpenRouter’s servers** — nothing heavy loads on your laptop

If a stage returns an empty file, the model may have burned its token budget on internal reasoning. Switch `DRAFT_MODEL` to DeepSeek (above) and rerun that stage.

---

## After the draft: how to use it as a writer

1. **Print `print.md`** (or export PDF/docx).
2. Treat it as clay: cut AI tics, deepen character, put *your* sentences in.
3. Suggested rewrite order:
   - **Structure** — does each movement raise cost? Protect the ending turn.
   - **Character** — make people specific; cut explanation that only serves “method.”
   - **Prose** — rhythm, dialogue, imagery that sound like you.
4. Prefer `redraft <n>` for one weak section over regenerating the whole story.
5. Run `diff` when you want a record of how much you changed for authorship notes.

---

## Non-negotiables

1. Local / private only — no public multi-user deploy
2. Your authorship first — approve premise + outline before prose; rewrite the draft
3. Provenance — every model call logged; `diff` for human-edit %
4. IP safety — no living-author imitation; no franchise characters/worlds; voice refs from your writing only
5. Hosted models via OpenRouter only (no local LLM / Ollama)
6. Low cost at volume; premium is opt-in
7. Quality over features — fewer solid stages beat many shallow ones

---

## Tests

```bash
source venv/bin/activate
pip install -r requirements-dev.txt
pytest tests/test_provider_openrouter.py tests/test_cost_budget.py \
  tests/test_checkpoints_and_fs.py tests/test_provenance_diff.py \
  tests/test_cliche_repetition.py -q
```

Tests use a mock provider and **never** call a real model.

---

## Quick reference

| Goal | Command |
|------|---------|
| New idea | `python shortstory.py spark "…" --slug my-slug` |
| Premise options | `python shortstory.py premise my-slug` |
| Unlock after editing premise | `python shortstory.py approve-premise my-slug` |
| Outline | `python shortstory.py outline my-slug --framework try_fail --words 5000` |
| Unlock after editing outline | `python shortstory.py approve-outline my-slug` |
| Draft all sections | `python shortstory.py draft my-slug` |
| Fix one section | `python shortstory.py redraft my-slug 3` |
| Build print file | `python shortstory.py assemble my-slug` |
| Cost | `python shortstory.py cost my-slug` |
| Local UI | `python webapp.py` → http://127.0.0.1:5001 |

More detail: `docs/MIGRATION.md`, `docs/pipeline.md`, `CONCEPTS.md`.
