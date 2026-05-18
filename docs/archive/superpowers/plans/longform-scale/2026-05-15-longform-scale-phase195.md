# Phase 195 - Stream Outline Chapters During Topology Creation

## Problem

Topology reads are windowed once a topology exists, but on-demand topology
creation still loaded the full `Outline` ORM object and then iterated
`outline.chapters`. For a thousand-chapter project, opening topology/relations
for the first time could select the full outline JSON in one ORM row.

## Change

- Added a topology regression test with a 1000-chapter outline.
- Changed topology creation to pass a streamed outline chapter iterator into
  `TopologyBuilder`.
- Added `_iter_outline_chapters()` using SQLite `json_each(outlines.chapters)`.
- Updated `TopologyBuilder.build()` to accept `Iterable[dict]` chapter input
  rather than an `Outline` ORM object.

## Tests

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_topologies.py::test_topology_creation_streams_outline_chapters_without_selecting_full_json -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_topologies.py::test_topology_creation_streams_outline_chapters_without_selecting_full_json -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_topologies.py backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_bounded_narrative_plan_window -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` (`599 passed`)
- GREEN: `npm run build` from `frontend`
- GREEN: `npm run test:unit` from `frontend` (`407 passed`)
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

First-time topology generation no longer selects the full outline chapter JSON.
It still builds and caches the complete topology, but chapter input is streamed
through SQL JSON iteration, which reduces one remaining longform-scale payload
spike.
