---

description: "Task list for Clean Code Refactor"
---

# Tasks: Clean Code Refactor

**Input**: Design documents from `specs/001-clean-refactor/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/api.md ✅, quickstart.md ✅

**Tests**: US4 is the test-suite user story — test tasks are included in Phase 6 as implementation of that story, not as TDD pre-steps.

**Organization**: Tasks are grouped by user story. US1–US3 touch different files and can run in parallel across developers. US4 depends on US1–US3 being complete.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)

---

## Phase 1: Setup

**Purpose**: Verify the baseline is green before any changes are made.

- [X] T001 Confirm `ruff check .` exits 0 and `pytest` passes on the unmodified codebase; add `mypy` to dev dependencies in `pyproject.toml` or `requirements.txt` if not already present

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: Shared type foundation used by every other module — must be complete before US1–US3 begin.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 Review and tighten type annotations in `src/equity_research_agent/models.py`: confirm every `TypedDict` field has an explicit type (no implicit `Any`); verify `_merge_dicts` signature is `(dict[str, str], dict[str, str]) -> dict[str, str]`; run `mypy src/equity_research_agent/models.py --ignore-missing-imports` with zero errors

**Checkpoint**: `models.py` mypy-clean — user story work can now begin in parallel.

---

## Phase 3: User Story 1 — Type Safety & Readability (Priority: P1) 🎯 MVP

**Goal**: `mypy` (standard mode) reports zero errors across `config.py`, `storage.py`, `cli.py`, and `web.py`; Flask route return types are explicit; no bare `dict` usage where `dict[str, Any]` is correct.

**Independent Test**: Run `mypy src/equity_research_agent/config.py src/equity_research_agent/storage.py src/equity_research_agent/cli.py src/equity_research_agent/web.py --ignore-missing-imports` — zero errors.

### Implementation for User Story 1

- [X] T003 [P] [US1] Add explicit return type `None` to `validate_for_generation()` and `validate_for_upload()` in `src/equity_research_agent/config.py`; remove the module-level `load_dotenv(".env")` call (redundant alongside `SettingsConfigDict(env_file=...)`) to prevent side effects during test imports
- [X] T004 [P] [US1] Fix `payload: dict | None` → `payload: dict[str, Any] | None` in the `save_local()` signature and fix `optimist_payload: dict | None`, `pessimist_payload: dict | None` parameters in `src/equity_research_agent/storage.py`; add explicit `-> PersistedArtifacts` return type to `save_local()` and `-> dict[str, str]` to `upload()`
- [X] T005 [P] [US1] Add return type annotations `-> argparse.Namespace` to `_parse_args()`, `-> str` to `_extract_pdf_text()` and `_load_input_text()`, and `-> None` to `main()` in `src/equity_research_agent/cli.py`
- [X] T006 [US1] Add `-> Response | tuple[Response, int]` return type to every Flask route function in `src/equity_research_agent/web.py`; change `_jobs: dict[str, dict]` to `_jobs: dict[str, dict[str, Any]]`; add `from flask import Response` import; add `-> dict[str, Any]` return type to `_public_job()`
- [X] T007 [US1] Run `mypy src/equity_research_agent/config.py src/equity_research_agent/storage.py src/equity_research_agent/cli.py src/equity_research_agent/web.py --ignore-missing-imports` and fix any remaining errors until the command reports zero issues

**Checkpoint**: US1 files are mypy-clean. Type safety story is independently verifiable.

---

## Phase 4: User Story 2 — Provider Abstraction (Priority: P2)

**Goal**: Adding a new LLM provider requires changes only in `src/equity_research_agent/llm.py`. The Azure dispatch block appears exactly once. All provider-specific logic is confined to `_call_provider()`.

**Independent Test**: Run `grep -c "chat.completions.create" src/equity_research_agent/llm.py` — result is `1`. Run `mypy src/equity_research_agent/llm.py --ignore-missing-imports` — zero errors.

### Implementation for User Story 2

- [X] T008 [US2] In `ResearchClient.__init__` in `src/equity_research_agent/llm.py`, declare instance attribute types before the provider branches: add `self._llm: ChatOpenAI | ChatAnthropic` declaration stub and `self._azure_client: AzureOpenAI` declaration stub so mypy can track their types across methods; keep existing initialisation logic unchanged
- [X] T009 [US2] Extract `_call_provider(self, system_prompt: str, user_prompt: str) -> str` private method in `src/equity_research_agent/llm.py` containing the full Azure/LangChain dispatch: the Azure branch calls `self._azure_client.chat.completions.create(...)`, extracts `content`, and returns `self._normalise_response_text(content or "")`; the LangChain branch calls `self._llm.invoke([SystemMessage(...), HumanMessage(...)])` and returns `self._normalise_response_text(response.content)`
- [X] T010 [US2] Refactor `generate()` in `src/equity_research_agent/llm.py` to build `prompt` via `build_task_prompt(...)` and then return `self._call_provider(BASE_SYSTEM_PROMPT, prompt)`; remove the inline Azure and LangChain dispatch blocks from this method
- [X] T011 [US2] Refactor `_generate_with_perspective()` in `src/equity_research_agent/llm.py` to build `prompt` via `build_task_prompt(..., perspective=perspective)` and then return `self._call_provider(BASE_SYSTEM_PROMPT, prompt)`; remove inline dispatch blocks
- [X] T012 [US2] Refactor `_generate_judge()` in `src/equity_research_agent/llm.py` to build `prompt` via `build_task_prompt(...)` with the judge preamble prepended and then return `self._call_provider(BASE_SYSTEM_PROMPT, prompt)`; remove inline dispatch blocks
- [X] T013 [US2] Replace all `Optional[str]` with `str | None` throughout `src/equity_research_agent/llm.py`; remove the `from typing import Optional` import; add `-> bool` to `debate_enabled` property; run `mypy src/equity_research_agent/llm.py --ignore-missing-imports` and fix any remaining errors

**Checkpoint**: `chat.completions.create` appears once; `llm.py` is mypy-clean; adding a fourth provider means editing only `_call_provider()` and `__init__`.

---

## Phase 5: User Story 3 — Duplication Elimination (Priority: P3)

**Goal**: No logic block appears in more than one location. `build_phase1_workflow()`, `build_phase2_workflow()`, and `build_workflow()` are all single-line delegations. `render_markdown()` calls `_build_header()`. Debate perspective assembly lives in one helper.

**Independent Test**: Run `grep -A 3 "def build_phase1_workflow" src/equity_research_agent/workflow.py` — body is a single `return _build_linear_graph(...)`. Run `grep -n "company_line" src/equity_research_agent/renderer.py` — only appears inside `_build_header()`.

### Implementation for User Story 3 (workflow.py)

- [X] T014 [US3] Add `import logging` and `logger = logging.getLogger(__name__)` at module level in `src/equity_research_agent/workflow.py`; in `_split_document_node`, replace the bare `except Exception: return {"document_sections": None}` with `except Exception as exc: logger.warning("Document splitting failed, falling back to full text: %s", exc); return {"document_sections": None}`
- [X] T015 [US3] Extract `_add_debate_perspective_outputs(state: ResearchState, result: dict[str, Any], *, with_morning_note: bool) -> None` in `src/equity_research_agent/workflow.py`: iterates over `[("debate_optimist", "debate_optimist"), ("debate_pessimist", "debate_pessimist")]`; for each, if the perspective key is present in state, calls `build_perspective_state` and populates `{prefix}_analyst_markdown`; if `with_morning_note` also populates `{prefix}_morning_note_markdown` and `{prefix}_payload`
- [X] T016 [US3] Refactor `_render_node()` in `src/equity_research_agent/workflow.py` to call `_add_debate_perspective_outputs(state, result, with_morning_note=True)` instead of the inline debate blocks; refactor `_render_analyst_node()` to call `_add_debate_perspective_outputs(state, result, with_morning_note=False)`; confirm debate output keys are identical to before
- [X] T017 [US3] Extract `_build_linear_graph(client: ResearchClient, tasks: list[str], render_name: str, render_fn: Callable[[ResearchState], dict[str, Any]], *, include_split: bool = False) -> CompiledStateGraph` in `src/equity_research_agent/workflow.py`; add necessary imports (`Callable`, `CompiledStateGraph` from `langgraph.graph`); implement: create `StateGraph(ResearchState)`, optionally add `split_document` node, add generation nodes for each task, add render node, chain edges `START → [split →] tasks[0] → ... → render_name → END`, return `graph.compile()`
- [X] T018 [US3] Replace bodies of `build_phase1_workflow()`, `build_phase2_workflow()`, and `build_workflow()` in `src/equity_research_agent/workflow.py` with single `return _build_linear_graph(...)` calls: phase1 uses `PHASE1_TASKS`, `"render_analyst"`, `_render_analyst_node`, `include_split=True`; phase2 uses `PHASE2_TASKS`, `"render_document"`, `_render_node`; full uses `PHASE1_TASKS + PHASE2_TASKS`, `"render_document"`, `_render_node`, `include_split=True`
- [X] T019 [US3] Add `-> dict[str, Any]` return type annotations to `_render_node`, `_render_analyst_node`, the inner function returned by `_split_document_node`, and the inner function returned by `_make_generation_node` in `src/equity_research_agent/workflow.py`; run `mypy src/equity_research_agent/workflow.py --ignore-missing-imports` and fix any remaining errors

### Implementation for User Story 3 (renderer.py — sequential; parallel with workflow.py tasks T014–T019)

- [X] T020 [US3] Refactor `render_markdown()` in `src/equity_research_agent/renderer.py` to call `_build_header(state)` at the top and use its return value in place of the inline `company_line` / `metadata_block` assembly; remove the duplicate timestamp and metadata-building code that duplicates `_build_header`
- [X] T021 [US3] Add explicit return type annotations to all functions in `src/equity_research_agent/renderer.py`: `_escape_markdown_chars` → `str`, `_build_header` → `str`, `render_analyst_markdown` → `str`, `render_morning_note_markdown` → `str`, `render_markdown` → `str`, `render_document_sections_markdown` → `str | None`, `build_perspective_state` → `ResearchState`; add `from typing import cast` and use `return cast(ResearchState, overlay)` in `build_perspective_state`; run `mypy src/equity_research_agent/renderer.py --ignore-missing-imports` with zero errors

**Checkpoint**: All duplication eliminated; `workflow.py` and `renderer.py` are mypy-clean; each public workflow builder is a single line.

---

## Phase 6: User Story 4 — Full Test Suite (Priority: P4)

**Goal**: `pytest` passes without live API credentials. Every public function has at least one behavioral test. A breaking change to any public function causes at least one test to fail.

**Independent Test**: Run `pytest -v` with no API keys set — all tests pass.

### Implementation for User Story 4

- [X] T022 [P] [US4] Create `tests/test_llm.py`: test `ResearchClient.__init__` raises `ValueError` for unknown provider; test `generate()` with `patch.object(client, "_call_provider", return_value="mocked")` confirms prompt is assembled and `_call_provider` is called once; test `generate()` raises `KeyError` for unknown task key; test `generate_with_debate()` returns a 3-tuple `(judge, optimist, pessimist)` with mocked `_call_provider`; test `_normalise_response_text` with string, list, and non-string inputs
- [X] T023 [P] [US4] Create `tests/test_workflow.py`: test `_build_linear_graph` returns a compiled graph with correct node names (inspect `graph.nodes`); test `build_phase1_workflow` and `build_phase2_workflow` compile without error using a `MagicMock(spec=ResearchClient)`; test `_split_document_node` returns `{"document_sections": None}` for short input; test `_split_document_node` logs a warning and returns `{"document_sections": None}` when `client.generate` raises an exception (use `caplog` fixture); test `_make_generation_node` calls `client.generate` and returns the result keyed by task name
- [X] T024 [P] [US4] Expand `tests/test_renderer.py`: add test for `render_analyst_markdown` contains "For Analyst Review" and all three phase-1 fields; add test for `render_morning_note_markdown` contains "Morning Note" and title/top_bullets; add test for `render_document_sections_markdown` returns `None` when `document_sections` is absent, and contains section headings when present; add test for `build_perspective_state` merges state fields correctly; add test for `_escape_markdown_chars` replaces `$` and `~`
- [X] T025 [P] [US4] Expand `tests/test_storage.py`: add test for debate artifact writing — call `save_local` with `optimist_analyst_markdown` and `pessimist_analyst_markdown` and confirm the corresponding paths exist; add test for `_simple_slugify` with special characters; add test for `save_local` with an explicit `run_dir` argument reuses that directory; add test for `source_file_bytes` writing
- [X] T026 [US4] Create `tests/test_cli.py`: test `_load_input_text` with `--text` argument; test `_load_input_text` with a `.txt` `--input-file` (use `tmp_path`); test `_load_input_text` raises `ValueError` when neither text nor file is provided and stdin is a tty; test `main()` with mocked `build_workflow` (returning a mock that returns a complete state dict) and mocked `ArtifactStore.save_local` — confirm it completes without error
- [X] T027 [US4] Create `tests/test_web.py` using `app.test_client()` from `src/equity_research_agent/web.py`: patch `_run_phase1_worker` to immediately set job status to `"awaiting_approval"` and test `POST /api/run` returns 202 with a `job_id`; test `GET /api/status/<job_id>` returns 200 for a known job and 404 for unknown; test `POST /api/approve/<job_id>` with `{"approved": false}` sets status to `"cancelled"`; test `POST /api/feedback/<job_id>` with invalid rating returns 400; test `GET /api/history` returns a JSON list; test `GET /api/history/<run_id>` returns 400 for path-traversal attempt

**Checkpoint**: All tests pass without API credentials; every module is covered by at least one behavioral test.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final integration validation — confirm all quality gates pass as a whole.

- [X] T028 [P] Run `mypy src/equity_research_agent/ --ignore-missing-imports` across all modules and fix any remaining cross-module type errors that surface only when all files are checked together
- [X] T029 [P] Run `ruff check .` and fix all lint issues (unused imports, line length, style warnings) across all modified files
- [X] T030 Run `pytest -v` to confirm all tests pass end-to-end with no live API credentials; confirm `test_chunking.py`, `test_renderer.py`, and `test_storage.py` still pass alongside new test files
- [X] T031 Verify quickstart.md duplication checks: (a) `grep -c "chat.completions.create" src/equity_research_agent/llm.py` returns `1`; (b) `grep -n "company_line" src/equity_research_agent/renderer.py` only matches inside `_build_header()`; (c) `build_phase1_workflow` body is a single `return _build_linear_graph(...)` call; (d) confirm `prompts.py` has no git diff; (e) confirm no provider SDK imports leak outside `llm.py` and `config.py`: `grep -rn "from openai\|from langchain\|from anthropic" src/equity_research_agent/ --include="*.py" | grep -v "llm.py\|config.py"` must return no output
- [X] T032 Run `make run-sample` or the inline CLI smoke test from CLAUDE.md to confirm end-to-end functional behaviour is unchanged after all refactoring
- [X] T033 Verify web UI and debate-ensemble regression: (a) in `tests/test_web.py`, add a test that when the job store contains debate perspective keys (`optimist_analyst_markdown`, `pessimist_analyst_markdown`), `GET /api/status/<job_id>` returns both keys as non-null in the response — confirming the debate output pathway through `_add_debate_perspective_outputs` is intact; (b) run the CLI in debate mode (`ENABLE_DEBATE=true python -m equity_research_agent.cli --text "..." --company Test`) if live credentials are available, or verify via the `test_workflow.py` suite that `build_phase1_workflow` and `build_phase2_workflow` correctly wire `_render_analyst_node` and `_render_node` respectively

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1, US2, US3 (Phases 3–5)**: All depend on Foundational; can run in parallel since they touch different files
  - US1: `config.py`, `storage.py`, `cli.py`, `web.py`
  - US2: `llm.py`
  - US3: `workflow.py`, `renderer.py`
- **US4 (Phase 6)**: Depends on US1, US2, US3 all being complete (tests target the refactored interfaces)
- **Polish (Phase 7)**: Depends on US4

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational — independent of US2 and US3
- **US2 (P2)**: Starts after Foundational — independent of US1 and US3
- **US3 (P3)**: Starts after Foundational — independent of US1 and US2
- **US4 (P4)**: Starts after US1, US2, and US3 are all complete

### Within Each User Story

- US2: T008 → T009 → T010 → T011 → T012 → T013 (each step builds on the previous)
- US3 workflow.py: T014 → T015 → T016 → T017 → T018 → T019 (sequential within file)
- US3 renderer.py: T020 → T021 (sequential within file; can run in parallel with workflow.py tasks)
- US4: T022–T025 can run in parallel; T026–T027 depend on the mocking patterns established in T022

---

## Parallel Execution Examples

### US1, US2, US3 in parallel (after T002):

```bash
# Developer A — US1 (type safety, config/storage/cli/web):
Task: T003 — config.py return types
Task: T004 — storage.py dict[str, Any]
Task: T005 — cli.py return types
Task: T006 — web.py Flask route return types
Task: T007 — mypy check US1 files

# Developer B — US2 (provider abstraction, llm.py):
Task: T008 — attribute type declarations
Task: T009 — extract _call_provider
Task: T010–T012 — refactor generate/perspective/judge
Task: T013 — mypy check llm.py

# Developer C — US3 (duplication, workflow.py + renderer.py):
Task: T014–T019 — workflow.py refactoring
Task: T020–T021 — renderer.py refactoring (can overlap with T014–T019)
```

### US4 parallel test writing (after US1–US3 complete):

```bash
# All four can run in parallel:
Task: T022 — tests/test_llm.py
Task: T023 — tests/test_workflow.py
Task: T024 — expand tests/test_renderer.py
Task: T025 — expand tests/test_storage.py
# Then sequentially:
Task: T026 — tests/test_cli.py
Task: T027 — tests/test_web.py
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002)
3. Complete Phase 3: US1 type annotations (T003–T007)
4. **STOP and VALIDATE**: `mypy src/equity_research_agent/config.py ... --ignore-missing-imports` — zero errors
5. The codebase is already partially improved and mypy-clean for 4 modules

### Incremental Delivery

1. Setup + Foundational → baseline clean
2. US1 (type safety for non-LLM modules) → 4 files mypy-clean
3. US2 (provider abstraction) → `llm.py` mypy-clean, 1-file provider addition proven
4. US3 (duplication elimination) → workflow/renderer DRY, zero duplication
5. US4 (test suite) → full behavioral coverage, no live API needed
6. Polish → all quality gates green together

### Single-Developer Sequential Strategy

With one developer: T001 → T002 → T003–T007 (can do in any order, different files) → T008–T013 → T014–T021 → T022–T027 → T028–T032
