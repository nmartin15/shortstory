# Project Structure — shortstoryfun

Private single-user drafting tool. CLI is primary; `webapp.py` is a thin local UI.

```text
shortstoryfun/
├── shortstory.py              # CLI launcher
├── webapp.py                  # Minimal local UI (127.0.0.1)
├── app.py                     # Thin alias → webapp
├── style.yaml                 # Your POV/tense/bans/voice refs
├── .env.example
├── config/
│   └── model_prices.yaml
├── prompts/                   # Stage prompt templates (Markdown)
├── src/shortstory/
│   ├── cli_app.py
│   ├── pipeline/              # Scene pipeline + checkpoints
│   ├── pipeline_legacy.py     # Old end-to-end pipeline (compat)
│   ├── providers/             # OpenRouter + mock
│   ├── cost/                  # $ tracking + budget cap
│   ├── provenance/            # JSONL + human-edit diff
│   ├── storage/               # stories/<slug>/ Markdown workspace
│   ├── style/                 # style bible + IP gate
│   ├── quality/               # cliché + repetition
│   ├── exports.py             # md/txt/docx/pdf/epub
│   └── …                      # genres, models, older services (legacy)
├── stories/                   # gitignored — per-story folders
├── docs/
│   ├── CONCEPTS.md
│   ├── pipeline.md
│   ├── MIGRATION.md
│   └── archive/               # Old planning/deploy docs
└── tests/                     # Mock-provider unit tests
```

## Day-to-day entry points

| Command | Purpose |
|---------|---------|
| `python shortstory.py …` | Primary drafting CLI |
| `python webapp.py` | Minimal local browser UI |
| `pytest tests/test_provider_openrouter.py …` | Core Phase 2 tests |

See [README.md](README.md) and [docs/MIGRATION.md](docs/MIGRATION.md).
