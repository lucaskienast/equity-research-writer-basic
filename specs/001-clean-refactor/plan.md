# Implementation Plan: Clean Code Refactor

**Branch**: `001-clean-refactor` | **Date**: 2026-03-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/001-clean-refactor/spec.md`

## Summary

Refactor the equity-research-writer-basic project to eliminate code duplication,
add full type annotations (mypy standard mode — zero errors), expand the test suite to
cover all modules with behavioral coverage, and make the provider abstraction explicit.
All business-owned prompt content in `prompts.py` is untouched. All existing
functionality is preserved with no regressions.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: LangGraph, langchain-openai, langchain-anthropic, openai (Azure),
Flask, pydantic-settings, pdfplumber, rich, pytest, ruff, mypy
**Storage**: Local filesystem (`output/`) + optional Azure Blob Storage
**Testing**: pytest (behavioral coverage, no live API calls)
**Target Platform**: macOS / Linux server
**Project Type**: CLI + web service (single process, threading for async web jobs)
**Performance Goals**: N/A — explicitly out of scope for this refactor
**Constraints**: No live LLM API calls in test suite; prompts.py untouched
**Scale/Scope**: Single-developer tooling; single-process Flask + background threads

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Deterministic Pipeline-First | ✅ Pass | Refactor preserves the ordered LangGraph chain; no new branching or side effects introduced into generation nodes |
| II. Prompt-Driven Editorial Control | ✅ Pass | `prompts.py` is explicitly out of scope (FR-003); refactor does not touch prompt text, task keys, or context field lists |
| III. Provider Agnosticism | ✅ Pass | FR-005 requires provider changes confined to ≤2 files; this refactor improves the current violation where Azure dispatch is duplicated 3× across methods |
| IV. Multi-Interface Access with Shared Core | ✅ Pass | FR-004 eliminates duplication between CLI and web UI execution; shared `ResearchClient` is strengthened not split |
| V. Structured, Auditable Output | ✅ Pass | FR-001 preserves all output artifacts, naming conventions, and Azure path structure |

**Post-Phase 0 re-check**: All gates still pass. The provider extraction (research decision R-1)
strictly strengthens Principle III. The workflow builder deduplication (R-2) preserves
Principle I's deterministic ordering exactly.

## Project Structure

### Documentation (this feature)

```text
specs/001-clean-refactor/
├── plan.md              # This file
├── research.md          # Phase 0 research findings
├── data-model.md        # Phase 1 data model
├── quickstart.md        # Phase 1 validation guide
├── contracts/
│   └── api.md           # Web API contracts
└── tasks.md             # Phase 2 output (/speckit.tasks — not yet created)
```

### Source Code (repository root)

```text
src/equity_research_agent/
├── __init__.py          # unchanged
├── config.py            # type annotation fixes; minor ruff cleanup
├── models.py            # annotation improvements (no structural change)
├── prompts.py           # UNTOUCHED — business-owned
├── llm.py               # extract _call_provider(); remove 3× Azure duplication
├── workflow.py          # extract _build_linear_graph(); add warning logging;
│                        # extract _add_debate_outputs() helper
├── renderer.py          # render_markdown() calls _build_header(); type fixes
├── storage.py           # dict → dict[str, Any] annotation fixes
├── cli.py               # add return type; minor annotation cleanup
└── web.py               # add return types to all Flask routes

tests/
├── test_renderer.py     # expand: analyst_md, morning_note, doc_sections,
│                        #          build_perspective_state, escape_chars
├── test_storage.py      # expand: debate artifacts, slugify, upload mock
├── test_chunking.py     # unchanged (already covers prompts + section parsing)
├── test_llm.py          # new: mock provider, generate(), generate_with_debate(),
│                        #      _call_provider dispatch, unknown task key, bad provider
├── test_workflow.py     # new: _make_generation_node, _split_document_node,
│                        #      _build_linear_graph, build_phase1/phase2/full workflow
├── test_cli.py          # new: _parse_args, _load_input_text, main() with mocked workflow
└── test_web.py          # new: api_run, api_status, api_approve, api_feedback,
                         #      api_history, api_history_run
```

**Structure Decision**: Single project (existing layout retained). No new directories
introduced. Tests are flat under `tests/` consistent with existing conventions.

## Phase 0: Research Findings

*See [research.md](./research.md) for full detail. Key decisions below.*

### R-1: Provider Dispatch Deduplication

**Decision**: Extract `_call_provider(system_prompt: str, user_prompt: str) -> str`
as a private method in `ResearchClient`.

**Problem found**: The 10-line Azure chat completion block and the 4-line LangChain
`.invoke()` block are copy-pasted verbatim in three methods: `generate()`,
`_generate_with_perspective()`, and `_generate_judge()`. This is the most severe
duplication in the codebase (FR-004 violation, Constitution Principle III violation).

**Solution**: A single `_call_provider(system_prompt, user_prompt) -> str` private
method centralises the Azure/LangChain dispatch. `generate()`,
`_generate_with_perspective()`, and `_generate_judge()` each assemble their prompt
strings and delegate the actual call to this method.

**Adding a new provider**: Change `_call_provider()` only. No other method changes.

### R-2: Workflow Builder Deduplication

**Decision**: Extract `_build_linear_graph(client, tasks, render_name, render_fn, *, include_split)`.

**Problem found**: `build_phase1_workflow()`, `build_phase2_workflow()`, and
`build_workflow()` all follow the identical StateGraph construction pattern: add nodes,
chain with edges, add render node, compile. Duplicated ~15 lines each.

**Solution**: A single `_build_linear_graph()` helper accepts a task list, render node
name/callable, and `include_split: bool`. All three public builders become one-liners.

### R-3: Render Node Debate Output Deduplication

**Decision**: Extract `_add_debate_perspective_outputs(state, result, *, with_morning_note)`.

**Problem found**: `_render_node()` and `_render_analyst_node()` both contain the
identical pattern of checking `state.get("debate_optimist")` / `state.get("debate_pessimist")`,
calling `build_perspective_state()`, and populating result keys. Duplicated ~12 lines.

**Solution**: A shared helper handles debate perspective assembly. `_render_node` calls
it with `with_morning_note=True`; `_render_analyst_node` calls it with
`with_morning_note=False`.

### R-4: Renderer Header Deduplication

**Decision**: `render_markdown()` must call `_build_header(state)` instead of
re-implementing the same metadata assembly logic.

**Problem found**: `render_markdown()` builds its own metadata block (company, ticker,
analyst, model, generated timestamp) — the same logic already exists in `_build_header()`.
This is a violation of the DRY principle with no justification.

### R-5: Type Annotation Gaps

**Decision**: Add explicit return types and fix `dict` → `dict[str, Any]` across all
modules. Use `ChatOpenAI | ChatAnthropic` union type for the `_llm` attribute. Add
`Response | tuple[Response, int]` return types to Flask routes.

**Specific gaps identified**:
- `llm.py`: `_llm` attribute has no declared type; `_azure_client` has no declared type
- `workflow.py`: `_render_node` returns `ResearchState` but actually returns a partial
  `dict`; should return `dict[str, Any]`
- `web.py`: All route functions lack return type annotations; mypy will warn
- `storage.py`: `payload: dict | None` → `dict[str, Any] | None`
- `renderer.py`: `build_perspective_state` casts `dict` to `ResearchState` without type
  safety; fix with proper overlay construction

### R-6: Logging

**Decision**: Replace the bare `except Exception: pass` in `_split_document_node` with
`except Exception: logger.warning("Document splitting failed: %s", exc, exc_info=True)`.
Use `logging.getLogger(__name__)` pattern in `workflow.py`.

### R-7: Test Infrastructure

**Decision**: Use `unittest.mock.patch` and `pytest` fixtures to mock at the
`ResearchClient._call_provider` boundary for `test_llm.py` and `test_workflow.py`.
For `test_web.py` use Flask's `test_client()`. For `test_cli.py` use
`unittest.mock.patch` on `build_workflow` and `ArtifactStore`.

**Existing tests preserved**: `test_renderer.py`, `test_storage.py`, `test_chunking.py`
pass unchanged; new tests expand coverage.

## Phase 1: Design Artifacts

*See [data-model.md](./data-model.md), [contracts/api.md](./contracts/api.md),
and [quickstart.md](./quickstart.md) for full detail.*

### Key Interface Changes

The public API of every module is **preserved exactly**. No function is renamed,
removed, or given a changed signature that breaks callers. Changes are:

1. `ResearchClient._call_provider(system_prompt, user_prompt) -> str` — new private
   method (not public API)
2. `_build_linear_graph(...)` — new private helper in `workflow.py` (not public API)
3. `_add_debate_perspective_outputs(...)` — new private helper in `workflow.py`
4. All public functions gain return type annotations (not signature changes)

### Constitution Check (Post-Design)

All five principles continue to pass. The refactored `_build_linear_graph` helper
preserves the exact same graph construction semantics (deterministic order, same edges).
The `_call_provider` extraction respects the existing provider guard logic exactly.
