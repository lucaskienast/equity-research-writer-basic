# Data Model: Clean Code Refactor

**Phase 1 output for**: `001-clean-refactor`
**Date**: 2026-03-27

## Overview

This refactor introduces no new persistent data entities. The central data structure
is `ResearchState` — a `TypedDict` that flows through the LangGraph pipeline. The
refactor improves its type safety but does not add or remove fields.

---

## ResearchState (existing — improved annotations)

The state dictionary passed through the LangGraph workflow. All fields are optional
(`total=False`) because nodes progressively populate them.

| Field | Type | Set by | Description |
|---|---|---|---|
| `raw_input` | `str` | CLI / web UI | Full source document text |
| `company` | `str \| None` | CLI / web UI | Company name metadata |
| `ticker` | `str \| None` | CLI / web UI | Ticker symbol metadata |
| `analyst` | `str \| None` | CLI / web UI | Requesting analyst metadata |
| `llm_model` | `str` | CLI / web UI | Provider/model label for display |
| `document_sections` | `dict[str, str] \| None` | `split_document` node | Parsed document sections (None if not split) |
| `summary_bullets` | `str` | Generation node | Phase 1 output |
| `unobvious_points` | `str` | Generation node | Phase 1 output |
| `spark` | `str` | Generation node | Phase 1 output |
| `financials` | `str` | Generation node | Phase 2 output |
| `commercial` | `str` | Generation node | Phase 2 output |
| `segments` | `str` | Generation node | Phase 2 output |
| `outlook` | `str` | Generation node | Phase 2 output |
| `top_bullets` | `str` | Generation node | Phase 2 output |
| `executive_summary` | `str` | Generation node | Phase 2 output |
| `title` | `str` | Generation node | Phase 2 output |
| `debate_optimist` | `Annotated[dict[str, str], _merge_dicts]` | Generation nodes (debate mode) | Per-task optimist outputs |
| `debate_pessimist` | `Annotated[dict[str, str], _merge_dicts]` | Generation nodes (debate mode) | Per-task pessimist outputs |
| `final_markdown` | `str` | `render_document` | Combined analyst + morning note markdown |
| `final_payload` | `dict[str, Any]` | `render_document` | Machine-readable JSON payload |
| `final_analyst_markdown` | `str` | `render_analyst` / `render_document` | Analyst review section only |
| `final_morning_note_markdown` | `str` | `render_document` | Morning note section only |
| `final_document_sections_markdown` | `str \| None` | `render_document` | Split document sections view |
| `debate_optimist_analyst_markdown` | `str` | `render_document` | Optimist analyst markdown |
| `debate_optimist_morning_note_markdown` | `str` | `render_document` | Optimist morning note |
| `debate_optimist_payload` | `dict[str, Any]` | `render_document` | Optimist JSON payload |
| `debate_pessimist_analyst_markdown` | `str` | `render_document` | Pessimist analyst markdown |
| `debate_pessimist_morning_note_markdown` | `str` | `render_document` | Pessimist morning note |
| `debate_pessimist_payload` | `dict[str, Any]` | `render_document` | Pessimist JSON payload |

**Annotation fixes in this refactor**:
- `final_payload`, `debate_optimist_payload`, `debate_pessimist_payload` are already
  typed as `dict[str, Any]` — confirmed correct.
- No field types change; only downstream usage in `renderer.py` and `storage.py`
  gains consistent `dict[str, Any]` instead of bare `dict`.

---

## ResearchClient (refactored internal structure)

| Attribute | Type | Notes |
|---|---|---|
| `_settings` | `Settings` | Injected configuration |
| `_provider` | `str` | Normalised provider name: `"openai"`, `"anthropic"`, `"azure"` |
| `_llm` | `ChatOpenAI \| ChatAnthropic` | Set for non-Azure providers only |
| `_azure_client` | `AzureOpenAI` | Set for Azure provider only |

**Key invariant**: Exactly one of `_llm` or `_azure_client` is initialised at
construction time based on `_provider`. `_call_provider()` guards on `_provider`
before accessing either attribute — same logic as before, now in one place.

---

## PersistedArtifacts (existing — no change)

A `dataclass(slots=True)` written by `ArtifactStore.save_local()`.

| Field | Type | Description |
|---|---|---|
| `run_dir` | `Path` | Timestamped output directory |
| `analyst_markdown_path` | `Path \| None` | Path to `analyst_review.md` |
| `morning_note_markdown_path` | `Path \| None` | Path to `morning_note.md` |
| `json_path` | `Path \| None` | Path to `research_note.json` |
| `document_sections_path` | `Path \| None` | Path to `document_sections.md` |
| `source_input_path` | `Path \| None` | Path to `source_input.txt` |
| `source_file_path` | `Path \| None` | Path to original uploaded file |
| `optimist_*` | `Path \| None` | Debate optimist artifact paths |
| `pessimist_*` | `Path \| None` | Debate pessimist artifact paths |
| `azure_urls` | `dict[str, str] \| None` | Azure blob URLs after upload |

**Annotation fix**: `ArtifactStore.save_local()` parameter `payload: dict | None`
→ `payload: dict[str, Any] | None`.

---

## Settings (existing — minor cleanup)

Pydantic-settings model. All fields unchanged. Minor cleanup: `load_dotenv(".env")`
call removed from module level (it is redundant alongside `SettingsConfigDict(env_file=...)`)
or moved inside a conditional to avoid side effects during import in tests.

---

## Job Store (in-memory, web.py)

The `_jobs` dict is an in-process store. Type improved from `dict[str, dict]` to
`dict[str, dict[str, Any]]`. No structural changes to the job record schema.

| Key | Type | Description |
|---|---|---|
| `status` | `str` | `running`, `awaiting_approval`, `phase2_running`, `done`, `error`, `cancelled` |
| `analyst_markdown` | `str \| None` | Phase 1 analyst output |
| `morning_note_markdown` | `str \| None` | Phase 2 morning note output |
| `optimist_*_markdown` | `str \| None` | Debate perspective outputs |
| `title` | `str \| None` | Generated title |
| `run_dir` | `str \| None` | Path to output directory |
| `error` | `str \| None` | Error message if status is `error` |
| `_state` | `ResearchState \| None` | Internal: passed between phase 1 and 2 workers |
| `_client` | `ResearchClient \| None` | Internal: shared client between phases |
| `_source_file_bytes` | `bytes \| None` | Internal: uploaded file bytes |
| `_source_file_name` | `str \| None` | Internal: uploaded file name |
