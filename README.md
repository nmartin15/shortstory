# shortstoryfun

Private, single-user short-story drafting tool. It produces **raw drafts** (about 2,000–7,500 words) for you to rewrite. It is not a product, not multi-user, and not a publishing platform.

## Setup

1. Create an [OpenRouter API key](https://openrouter.ai/keys) **with a spending limit**.
2. Copy env template and edit:

```bash
cp .env.example .env
# set OPENROUTER_API_KEY=...
```

3. Install deps (Python 3.10+ recommended):

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # for tests
```

4. Put short samples of **your own writing** in `style.yaml` under `voice_references`.

## First story (CLI)

```bash
python shortstory.py spark "A night clerk in Flagstaff finds a ledger that rewrites itself"
python shortstory.py premise flagstaff-ledger
# edit stories/flagstaff-ledger/01_premise.md — pick or rewrite one option
python shortstory.py approve-premise flagstaff-ledger
python shortstory.py outline flagstaff-ledger --framework story_circle --words 5000
# edit stories/flagstaff-ledger/02_outline.md if needed
python shortstory.py approve-outline flagstaff-ledger
python shortstory.py draft flagstaff-ledger
python shortstory.py continuity flagstaff-ledger
python shortstory.py assemble flagstaff-ledger
python shortstory.py cost flagstaff-ledger
python shortstory.py diff flagstaff-ledger
```

Premium model (manual only):

```bash
python shortstory.py draft flagstaff-ledger --premium
```

Export: `md`, `txt`, `docx`, `pdf`, `epub`:

```bash
python shortstory.py export flagstaff-ledger --format docx
```

## Minimal local UI

```bash
python webapp.py
# open http://127.0.0.1:5000
```

## Models (from `.env`, never hardcoded in call sites)

| Var | Default | When |
|-----|---------|------|
| `DRAFT_MODEL` | `qwen/qwen3.8-27b` | Default for all stages |
| (alt) | `deepseek/deepseek-v4.1-flash` | Set as `DRAFT_MODEL` if you prefer |
| `PREMIUM_MODEL` | `moonshotai/kimi-k3.1-pro` | Only with `--premium` / UI checkbox |
| `BUDGET_CAP_USD` | e.g. `1.00` | Stops a run before exceeding |

Prices for estimates live in `config/model_prices.yaml`.

## Story folder layout

```text
stories/<slug>/
  00_spark.md
  01_premise.md
  02_outline.md
  scenes/01.md …
  03_continuity.md
  draft_v1.md
  provenance.jsonl
  costs.jsonl
  meta.yaml
```

## Non-negotiables

1. Local / private only
2. You approve premise + outline before prose
3. Every model call is logged; `diff` shows how much you changed
4. No living-author imitation; no franchise IP; voice refs from your writing only
5. Hosted models via OpenRouter only
6. Cheap volume drafting; premium is opt-in
7. Quality over features — scene-by-scene drafts

## Tests

```bash
pytest tests/test_provider_openrouter.py tests/test_cost_budget.py \
  tests/test_checkpoints_and_fs.py tests/test_provenance_diff.py \
  tests/test_cliche_repetition.py -q
```

Tests use `MockProvider` and never call a real model.
