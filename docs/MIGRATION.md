# Migration notes (Phase 2 rebuild)

## What changed

- **OpenRouter** replaced direct Gemini (`OPENROUTER_API_KEY`, `DRAFT_MODEL`, `PREMIUM_MODEL`).
- **Scene-based pipeline** with premise/outline **checkpoints** before prose.
- Stories live in **`stories/<slug>/` Markdown**, not only SQLite.
- **CLI** (`python shortstory.py …`) is primary; **`webapp.py`** is a minimal local UI.
- Production stack removed from the default path: Redis/RQ, gunicorn, Docker, deploy workflow.

## Still present (legacy)

- `src/shortstory/pipeline_legacy.py` and older Flask `app.py` / services remain for reference and older tests.
- Prefer `webapp.py` + the new `pipeline` package for day-to-day drafting.

## First-run checklist

1. Copy `.env.example` → `.env` and set OpenRouter key with a spend limit.
2. Edit `style.yaml` voice references (your writing only).
3. Run `python shortstory.py spark "…"`.
