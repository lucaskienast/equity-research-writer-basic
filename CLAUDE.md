# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run the workflow on sample input
make run-sample

# Run tests
pytest
# or
make test

# Lint
ruff check .
# or
make lint

# Start the Flask web UI at http://localhost:5000
make run-web
# or
python -m equity_research_agent.web

# Run with inline text
python -m equity_research_agent.cli --text "..." --company "Acme" --ticker ACM --analyst "J. Smith"

# Inline run example
python -m equity_research_agent.cli \
  --input-file examples/Ocado_FY25_Results_Announcement.pdf \
  --company "Ocado Group PLC" \
  --ticker OCDO \
  --analyst "J. Smith"

# Run from a file
python -m equity_research_agent.cli --input-file examples/sample_input.txt --company "Acme" --ticker ACM

# Force Azure upload for a run
python -m equity_research_agent.cli --input-file examples/sample_input.txt --company "Acme" --upload
```

## Architecture

This is a deterministic LangGraph workflow that takes raw text (e.g. an RNS, trading update, or email) and produces a structured equity research note in Markdown and JSON.

### Data flow

```
CLI (cli.py) / Flask UI (web.py) → ResearchClient (llm.py) → LangGraph workflow (workflow.py)
  → 10 sequential generation nodes → render_document node (produces analyst_review.md + morning_note.md + JSON)
  → ArtifactStore (storage.py) → local output/ dir → optional Azure Blob upload
```

### State machine (`workflow.py` + `models.py`)

The graph is a linear chain of nodes, each writing one field into `ResearchState` (a `TypedDict`). Node order matters because later nodes receive prior sections as context:

1. `summary_bullets` → 2. `unobvious_points` → 3. `spark` → 4. `financials` → 5. `commercial` → 6. `segments` → 7. `outlook` → 8. `top_bullets` → 9. `executive_summary` → 10. `title` → 11. `render_document`

Each generation node is created by `_make_generation_node(client, task_key)`, which calls `client.generate(task_key, state)`.

### Prompt system (`prompts.py`)

The most important file for editorial control. Structure:

- `BASE_SYSTEM_PROMPT`: global role, tone, style rules, and financial terminology definitions — injected as the `SystemMessage` on every LLM call.
- Per-task prompt constants (e.g. `HIGH_LEVEL_SUMMARY_BULLETS_PROMPT`, `THE_SPARK_PROMPT`, etc.): define output format, length limits, and step-by-step instructions per section.
- `TASK_SPECS` dict: maps each `task_key` to its `instructions` and a `context` list — the list of prior state fields to inject as previously generated context.
- `build_task_prompt()`: assembles the final human message by combining task name, instructions, metadata (company/ticker/analyst), source text, and prior context fields.

To change house style, tone, section structure, or output format, edit the prompt constants and/or `TASK_SPECS`.

### LLM client (`llm.py`)

`ResearchClient` wraps either `langchain_openai.ChatOpenAI` or `langchain_anthropic.ChatAnthropic` depending on `LLM_PROVIDER`. Each call sends a fixed `SystemMessage` (base prompt) plus a `HumanMessage` (task-specific prompt with context). The client is stateless — all context accumulates in `ResearchState`.

### Web UI (`web.py`)

A Flask application exposing:
- `GET /` — serves the dark/light mode UI (`templates/index.html`)
- `POST /api/run` — accepts form fields (`text`, `company`, `ticker`, `analyst`) and an optional file upload (PDF or TXT); starts the workflow in a background thread and returns a `job_id`
- `GET /api/status/<job_id>` — returns job status (`running` | `done` | `error`) and the generated markdown once complete

Jobs run asynchronously via `threading.Thread`, so the UI can poll for results without blocking.

### Config (`config.py`)

`Settings` uses `pydantic-settings` and reads from `.env`. Key variables:

| Variable | Default |
|---|---|
| `LLM_PROVIDER` | `openai` (`openai` or `anthropic`) |
| `LLM_MODEL` | `gpt-4o-mini` |
| `LLM_TEMPERATURE` | `0.1` |
| `LLM_MAX_TOKENS` | `1400` |
| `OPENAI_API_KEY` | (required when `LLM_PROVIDER=openai`) |
| `ANTHROPIC_API_KEY` | (required when `LLM_PROVIDER=anthropic`) |
| `AZURE_STORAGE_CONNECTION_STRING` | (required for upload) |
| `AZURE_BLOB_CONTAINER` | `equity-research-output` |
| `UPLOAD_TO_AZURE` | `false` |
| `LOCAL_OUTPUT_DIR` | `output` |

### Output (`renderer.py`, `storage.py`)

`renderer.py` assembles three output artifacts from all state fields. `ArtifactStore` in `storage.py` writes a timestamped directory under `output/` (e.g. `output/20260301T101500Z-acme-demand-slows/`) containing:

- `analyst_review.md` — full structured note for the analyst
- `morning_note.md` — condensed morning note format
- `research_note.json` — machine-readable JSON payload

Optionally uploads all three to Azure Blob Storage using the path convention `{prefix}/YYYY/MM/DD/{run-id}/`.

## Package layout

Source code lives under `src/equity_research_agent/` (editable install maps this to `equity_research_agent`). Tests are in `tests/` and cover renderer and storage logic. The `examples/` directory contains sample input text files.
