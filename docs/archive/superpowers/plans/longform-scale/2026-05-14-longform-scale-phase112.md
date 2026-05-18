# Phase 112 - Million Word Smoke Baseline

## Goal
Validate the current longform foundation against a synthetic thousand-chapter, million-word project and capture the next bottleneck with evidence.

## Command
`.\backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --cleanup`

## Result
- Status: passed.
- Chapters: `1000`.
- Words per chapter: `1000`.
- Total words: `1000000`.
- Longform memories: `1061` total: `1000` chapter, `50` arc, `10` volume, `1` global.
- Retrieval documents: `2061`: `1000` chapter, `1061` longform memory.
- Retrieval chunks: `3061`.
- Retrieval terms: `247265`.
- Retrieval embeddings: `3061`.
- Context sections: `global`, `volume`, `arc`, `recent_chapters`, `query_aware_retrieval`.
- Prompt context length: `3750` characters.
- Background task completed `1000 / 1000` chapters.

## Timings
- Seed project: `93 ms`.
- Task progress: `18 ms`.
- Memory rebuild: `320 ms`.
- Retrieval reindex: `13397 ms`.
- Context build: `442 ms`.
- Task complete: `11 ms`.
- Total elapsed: `14284 ms`.

## Finding
The current system can complete the million-word synthetic smoke successfully. The dominant cost is retrieval reindexing, which accounts for almost the entire elapsed time. The next optimization target should be retrieval indexing throughput, especially term generation and document/chunk processing for full-project reindex paths.
