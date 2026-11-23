# Pipeline Architecture — shortstoryfun

> See [CONCEPTS.md](docs/CONCEPTS.md) for distinctiveness / voice / memorability.  
> See [docs/MIGRATION.md](docs/MIGRATION.md) for the Phase 2 rebuild notes.

## Stages (current)

1. **Spark** — save raw author input (`00_spark.md`); IP gate rejects franchises / living authors.
2. **Premise** — model proposes 3 options; **you approve** before continuing.
3. **Outline** — 6–12 scenes under Story Circle / try-fail / MICE; **you approve** before prose.
4. **Scene draft** — one scene per model call (cheap `DRAFT_MODEL` by default; `--premium` opt-in).
5. **Quality** — cliché + repetition check; one flagged-paragraph regen.
6. **Continuity** — report only (no auto-rewrite).
7. **Assemble** — stitch to `draft_v1.md` with word-count report. Always labeled **RAW DRAFT**.

Nothing drafts prose until premise **and** outline are approved.

## Storage

```text
stories/<slug>/
  00_spark.md
  01_premise.md
  02_outline.md
  scenes/
  03_continuity.md
  draft_v1.md
  provenance.jsonl
  costs.jsonl
  meta.yaml
```

## Models

- OpenRouter only (`OpenAICompatibleProvider`)
- `DRAFT_MODEL` (default `qwen/qwen3.8-27b`) and `PREMIUM_MODEL` (default `moonshotai/kimi-k3.1-pro`) from `.env`
- Premium never selected automatically

## Legacy

`pipeline_legacy.py` (`ShortStoryPipeline`) remains for older tests/services. New work uses `src/shortstory/pipeline/`.
