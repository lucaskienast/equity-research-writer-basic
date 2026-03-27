<!--
SYNC IMPACT REPORT
==================
Version change: [TEMPLATE] → 1.0.0
Modified principles: All placeholders replaced (initial ratification)
Added sections:
  - Core Principles (5 principles fully defined)
  - Technology Constraints
  - Development Workflow
  - Governance
Removed sections: None
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ Constitution Check gates align with principles below
  - .specify/templates/spec-template.md ✅ No mandatory section changes required
  - .specify/templates/tasks-template.md ✅ Task categories (observability, testing) consistent
  - .specify/templates/agent-file-template.md ✅ No outdated agent-specific references found
Deferred TODOs: None
-->

# Equity Research Writer Constitution

## Core Principles

### I. Deterministic Pipeline-First

The core generation workflow MUST be implemented as a deterministic, linearly ordered
LangGraph state machine. Node order is semantically load-bearing: each node receives
the outputs of all prior nodes as context, so reordering nodes changes the meaning of
generated content. No randomness, retries with state mutation, or conditional branching
MUST be introduced into the generation chain without explicit constitution amendment.

Generation nodes MUST be pure: they receive `ResearchState`, call the LLM client once,
and return only the field(s) they own. Side effects (file I/O, network calls) MUST NOT
occur inside generation nodes.

**Rationale**: Determinism ensures reproducibility of research outputs and makes
debugging tractable. Editorial consistency across runs depends on a fixed execution
order.

### II. Prompt-Driven Editorial Control

All style, tone, section structure, length limits, and output format decisions MUST
live exclusively in `prompts.py`. LLM clients (`llm.py`) MUST remain stateless
wrappers that forward `SystemMessage` + `HumanMessage` to the provider. No hardcoded
editorial content (headings, phrases, formatting rules) MUST appear in workflow,
renderer, or web layer code.

To change house style, section ordering, or output format, editing `prompts.py` MUST
be sufficient — no other files SHOULD require modification.

**Rationale**: Separating editorial intent from execution code allows non-engineers to
tune output quality without touching infrastructure code.

### III. Provider Agnosticism

The system MUST remain compatible with at least OpenAI and Anthropic LLM providers via
a single `LLM_PROVIDER` config toggle. All provider-specific instantiation MUST be
confined to `llm.py` and `config.py`. No provider SDK imports MUST appear outside
those two files. New providers MAY be added by extending `llm.py` only.

**Rationale**: Avoids vendor lock-in and allows cost/capability trade-offs without
architectural changes.

### IV. Multi-Interface Access with Shared Core

The generation workflow MUST be accessible via both the CLI (`cli.py`) and the Flask
web UI (`web.py`). Both interfaces MUST share the same `ResearchClient` and LangGraph
workflow — no interface-specific generation logic is permitted. The web UI MUST execute
jobs asynchronously (background thread) to remain non-blocking. The CLI MUST support
inline text input, file input (PDF and TXT), and forced Azure upload via flags.

**Rationale**: Consistency between interfaces prevents output divergence and ensures
the CLI remains a reliable debugging tool for web UI issues.

### V. Structured, Auditable Output

Every run MUST produce a timestamped output directory containing three artifacts:
`analyst_review.md`, `morning_note.md`, and `research_note.json`. The directory naming
convention (`YYYYMMDDTHHMMSSZ-{slug}/`) MUST be preserved to support chronological
sorting and Azure path conventions. When the multi-agent debate ensemble
(optimist/pessimist/judge) is enabled, all three perspectives MUST be surfaced in the
web UI with visual differentiation. The Azure upload path convention
(`{prefix}/YYYY/MM/DD/{run-id}/`) MUST remain stable across releases.

**Rationale**: Auditability and reproducibility of research notes are regulatory and
operational requirements. The debate ensemble output must be inspectable, not hidden.

## Technology Constraints

The technology stack is fixed for this project. Deviations require constitution
amendment.

- **Language**: Python 3.11+
- **Workflow engine**: LangGraph (`langgraph`)
- **LLM clients**: `langchain_openai.ChatOpenAI` and `langchain_anthropic.ChatAnthropic`
- **Config management**: `pydantic-settings` reading from `.env`
- **Web framework**: Flask (synchronous, single-process, threading for async jobs)
- **Testing**: `pytest`; test coverage MUST include renderer and storage logic
- **Linting**: `ruff` — all code MUST pass `ruff check .` before merge
- **Package layout**: `src/equity_research_agent/` with editable install (`pip install -e ".[dev]"`)
- **PDF parsing**: Handled at the interface layer (CLI/web) before passing raw text to
  the workflow; the workflow itself MUST only receive plain text strings
- **External storage**: Azure Blob Storage (optional); local `output/` directory always
  written regardless of upload setting

## Development Workflow

- All new features MUST be exercised via `make run-sample` or an equivalent inline CLI
  invocation before merge.
- Changes to prompts alone (no code changes) MUST still pass `pytest` and `ruff`.
- The `render_document` / `render_analyst` nodes are the sole consumers of
  `ResearchState` for output assembly; new output sections MUST be added through the
  renderer layer, not inline in generation nodes.
- When adding a new generation task: (1) add a prompt constant and entry in
  `TASK_SPECS` in `prompts.py`, (2) add the task key to the ordered list in
  `workflow.py`, (3) add the field to `ResearchState` in `models.py`, (4) update
  `renderer.py` to include the field in output artifacts.
- The debate ensemble (optimist/pessimist/judge) MUST remain opt-in via config; the
  single-agent path MUST always be functional and the default.

## Governance

This constitution supersedes all other development practices and conventions within
this repository. Any practice not covered here defaults to the principle of minimum
necessary complexity (YAGNI).

**Amendment procedure**:
1. Propose the change with written rationale referencing the principle(s) affected.
2. Increment `CONSTITUTION_VERSION` per semantic versioning rules defined below.
3. Update `LAST_AMENDED_DATE` to the date of change.
4. Propagate any impacts to templates (`.specify/templates/`) and this document's
   Sync Impact Report header comment.

**Versioning policy** (semantic versioning applied to governance):
- **MAJOR**: Backward-incompatible removal or redefinition of a Core Principle.
- **MINOR**: New principle or section added, or materially expanded guidance.
- **PATCH**: Clarifications, wording, or non-semantic refinements.

**Compliance review**: All PRs MUST verify that changes do not violate Core Principles
I–V. The Constitution Check section in `plan-template.md` gates plan approval on this
verification. Complexity deviations MUST be justified in the plan's Complexity Tracking
table.

**Runtime guidance**: See `CLAUDE.md` for commands, architecture overview, and
per-module descriptions used during active development sessions.

**Version**: 1.0.0 | **Ratified**: 2026-03-27 | **Last Amended**: 2026-03-27
