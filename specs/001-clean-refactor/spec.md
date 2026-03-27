# Feature Specification: Clean Code Refactor

**Feature Branch**: `001-clean-refactor`
**Created**: 2026-03-27
**Status**: Draft
**Input**: User description: "refactor clean code - refactor and clean up the whole project so that it keeps all its functionalities but has easy to read code, is maintainable, fully tested, has no code duplication, and works for all llm providers. there should be no warnings for any return types ie all return types should be correct. prompts should remain the same as those are provided by the business."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer Reads and Understands the Codebase (Priority: P1)

A developer new to the project opens the codebase and can understand the purpose and
flow of any module within a short reading session. Functions and classes have single,
clear responsibilities. Type annotations are complete and accurate throughout, so IDE
tooling provides reliable auto-complete and inline error feedback with zero type
warnings.

**Why this priority**: Readability and type safety are the foundation of every other
quality goal. Without them, maintenance, testing, and extension all become harder.
This story delivers immediate value to anyone working with the code.

**Independent Test**: Run a static type checker against the refactored source — it
reports zero type errors or return-type warnings. A developer reviewing any module can
state its single responsibility without reading other files.

**Acceptance Scenarios**:

1. **Given** the refactored codebase, **When** a developer runs a static type checker,
   **Then** zero type errors or return-type warnings are reported across all source files.
2. **Given** any public function in the codebase, **When** a developer reads only that
   function's signature, **Then** the function's inputs, outputs, and side effects are
   unambiguous without reading the body.
3. **Given** any module, **When** a developer reads it in isolation, **Then** its single
   responsibility is clear and it does not contain logic that belongs elsewhere.

---

### User Story 2 - Developer Adds a New LLM Provider (Priority: P2)

A developer wants to integrate a third LLM provider. The provider abstraction is clean
enough that they can add support by modifying only the provider-specific layer, without
touching workflow, prompt, or rendering logic. The new provider works identically for
both the single-agent and debate-ensemble paths.

**Why this priority**: Provider agnosticism is a core project principle. If the
refactored code leaks provider details across layers, the refactor has not achieved its
main structural goal.

**Independent Test**: Trace the code path for adding a hypothetical third provider and
verify that zero changes are needed outside the provider layer. Confirm by inspection
that at most 2 files require modification.

**Acceptance Scenarios**:

1. **Given** the refactored provider abstraction, **When** a developer adds a new
   provider, **Then** the only files requiring modification are within the
   provider-specific layer.
2. **Given** a new provider configured via the provider setting, **When** the workflow
   runs, **Then** all generation nodes, the debate ensemble, and both CLI and web UI
   interfaces function without any modification.

---

### User Story 3 - Developer Adds a New Generation Section (Priority: P3)

A developer wants to add a new section to the research note output. The process is
self-evident from the code structure: adding the node registration and state field are
the only steps required, and no existing logic needs to be duplicated.

**Why this priority**: The generation pipeline will evolve as business requirements
change. A non-duplicated structure makes extension safe and the process predictable.

**Independent Test**: Confirm that no boilerplate code from existing nodes needs to be
copy-pasted when adding a new task. Verify zero duplicated node-construction logic
exists between Phase 1 and Phase 2 workflow setup.

**Acceptance Scenarios**:

1. **Given** the refactored workflow, **When** a developer adds a new task key,
   **Then** no logic from existing nodes needs to be duplicated.
2. **Given** the refactored codebase, **Then** there is no duplicated logic between
   Phase 1 and Phase 2 workflow construction, between debate and non-debate generation
   paths, or between CLI and web UI execution.

---

### User Story 4 - Developer Runs the Full Test Suite (Priority: P4)

A developer makes a change and runs the test suite. Tests cover all meaningful
behaviours: rendering logic, storage logic, provider client construction and dispatch,
workflow node execution, and both CLI and web UI entry points. Tests are independent
and clearly named so that a failure immediately points to the broken behaviour.
No live provider API calls are needed to run the suite.

**Why this priority**: Untested code cannot be confidently refactored or extended. The
current test coverage covers only renderer and storage; this story expands it to
cover all modules.

**Independent Test**: Run `pytest` against the refactored project — all tests pass,
all modules are exercised, and no live API credentials are required.

**Acceptance Scenarios**:

1. **Given** the refactored test suite, **When** `pytest` is run without live API
   credentials, **Then** all tests pass and cover renderer, storage, provider client,
   workflow nodes, CLI, and web UI.
2. **Given** any generation node, **When** tested in isolation, **Then** the test
   does not require a live provider call (provider is mocked at the interface boundary).
3. **Given** a breaking change is introduced to any public function, **When** tests
   run, **Then** at least one test fails and identifies the broken behaviour by name.

---

### Edge Cases

- What happens when the provider client returns an unexpected response that does not
  match the expected string output — the client MUST NOT silently return None or an
  untyped value; it MUST normalise the response to a non-empty string (using a typed
  normalisation function) so that callers always receive a `str`. If the response is
  entirely unparseable, a `TypeError` MUST be raised with a descriptive message.
- How does the system handle a provider name in config that has no corresponding client
  implementation — the provider layer MUST raise a clear, typed error at startup
  before any generation begins.
- What happens if a generation node returns a field that does not exist in the state
  type — static type checking MUST catch this before runtime.
- What happens when best-effort optimisation steps (e.g., document splitting) fail
  internally — the exception MUST be logged at warning level and the step MUST fall
  back gracefully; the overall workflow MUST continue uninterrupted.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The refactored codebase MUST preserve all existing end-to-end
  functionality: CLI execution, web UI execution, single-agent mode, debate-ensemble
  mode, local output writing, and optional cloud upload.
- **FR-002**: All public functions and methods MUST carry accurate type annotations;
  the codebase MUST produce zero errors or warnings when checked with `mypy`
  (standard mode).
- **FR-003**: Business-provided prompt constants and the task specification mapping
  in `prompts.py` MUST remain unchanged; refactoring MUST NOT alter prompt text,
  task keys, or context field lists.
- **FR-004**: Code duplication MUST be eliminated across shared logic between Phase 1
  and Phase 2 workflow construction, between debate and non-debate generation paths,
  and between CLI and web UI job execution.
- **FR-005**: The provider abstraction MUST be explicit; adding a new provider MUST
  require changes only within the provider-specific layer, with no modifications to
  workflow, prompt, renderer, or interface code.
- **FR-006**: The test suite MUST cover renderer logic, storage logic, provider client
  construction, workflow node execution, CLI entry point, and web UI endpoints.
- **FR-007**: All tests MUST be runnable without live provider API calls; provider
  interactions MUST be mockable at a well-defined boundary.
- **FR-008**: Linting MUST produce zero warnings or errors on the refactored codebase.
- **FR-009**: Best-effort workflow steps that catch exceptions MUST log those exceptions
  at warning level; silent swallowing of exceptions is not permitted. Graceful
  degradation behaviour (fallback result) MUST be preserved.

### Key Entities

- **ResearchState**: Typed dictionary holding all intermediate and final outputs of
  the generation pipeline; all fields MUST be explicitly typed with no implicit
  untyped values.
- **ResearchClient**: Provider-agnostic interface; MUST expose a typed contract that
  concrete provider implementations fulfil without leaking provider details upward.
- **GenerationNode**: A callable unit in the pipeline; MUST have a consistent typed
  signature with no variation between nodes.
- **ArtifactStore**: Output writer for local file creation and optional cloud upload;
  interface MUST be typed and independently testable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `mypy` (standard mode) reports zero errors or warnings across all source
  files after refactoring.
- **SC-002**: Linting reports zero issues after refactoring.
- **SC-003**: All existing end-to-end behaviours (CLI, web UI, single-agent,
  debate-ensemble, local output, cloud upload) continue to work identically to before
  the refactor with no functional regression.
- **SC-004**: The test suite provides behavioral coverage: every public function has at
  least one test, all edge cases listed in the spec are covered, and a breaking change
  to any public function causes at least one test to fail. No specific line-coverage
  percentage is required.
- **SC-005**: Adding a new provider requires changes in at most 2 files, as verifiable
  by code inspection.
- **SC-006**: No function or block of logic appears in more than one location in the
  codebase, as verifiable by code review.

## Clarifications

### Session 2026-03-27

- Q: What constitutes "fully tested" — specific line-coverage percentage or behavioral coverage? → A: Behavioral coverage only — every public function has at least one test; all edge cases from the spec are tested; no numeric % required.
- Q: Which static type checker and strictness level? → A: mypy standard mode.
- Q: Should silent exception swallowing in the workflow layer be changed? → A: Log at warning level, preserve graceful degradation fallback behaviour.

## Assumptions

- Prompt text, task keys, and context field lists in `prompts.py` are owned by the
  business and are explicitly out of scope for this refactor.
- The LangGraph, Flask, and config management dependencies are retained; no framework
  migrations are in scope.
- Python 3.11+ type features are available and SHOULD be used where they improve
  clarity and type safety.
- Cloud storage integration is tested via a mock or stub; live credentials are not
  required for the test suite.
- Performance characteristics of the workflow are unchanged by the refactor; no
  performance optimisation is in scope.
- The `examples/` directory and `output/` directory layout remain unchanged.
- The `templates/index.html` and all web UI visual output remain unchanged.
