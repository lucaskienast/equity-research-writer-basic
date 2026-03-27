# Research: Clean Code Refactor

**Phase 0 output for**: `001-clean-refactor`
**Date**: 2026-03-27

## R-1: Provider Dispatch Deduplication

### Problem

`llm.py` contains three methods — `generate()`, `_generate_with_perspective()`,
`_generate_judge()` — that each duplicate the full provider dispatch logic:

```
Azure path (10 lines):
  azure_client.chat.completions.create(model, messages, temperature, max_tokens)
  → extract content from response.choices[0].message.content
  → _normalise_response_text(content or "")

LangChain path (4 lines):
  self._llm.invoke([SystemMessage(...), HumanMessage(...)])
  → _normalise_response_text(response.content)
```

This duplication exists in all three methods verbatim. Adding a new provider requires
changes in 3 places instead of 1 — a Constitution Principle III violation.

### Decision

Extract `_call_provider(system_prompt: str, user_prompt: str) -> str` as a single
private method. All three generation methods assemble their prompt strings and delegate
to this method.

```python
def _call_provider(self, system_prompt: str, user_prompt: str) -> str:
    if self._provider == "azure":
        response = self._azure_client.chat.completions.create(
            model=self._settings.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self._settings.llm_temperature,
            max_tokens=self._settings.llm_max_tokens,
        )
        content: str | None = None
        if response.choices and response.choices[0].message:
            content = response.choices[0].message.content
        return self._normalise_response_text(content or "")
    response = self._llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ])
    return self._normalise_response_text(response.content)
```

### Rationale

- Single location for provider dispatch — adding a new provider touches this method only
- `generate()`, `_generate_with_perspective()`, `_generate_judge()` become simpler:
  each assembles prompt strings, calls `_call_provider(BASE_SYSTEM_PROMPT, prompt)`
- `_normalise_response_text` stays as a static method for testability

### Alternatives Considered

- **Protocol/interface approach** (e.g., `LLMBackend` protocol with `call()` method):
  Rejected — more indirection than needed for 3 providers. The private method approach
  achieves the same isolation with less structural change.
- **Keeping duplication**: Rejected — direct Constitution Principle III violation.

---

## R-2: Workflow Builder Deduplication

### Problem

`build_phase1_workflow()`, `build_phase2_workflow()`, and `build_workflow()` all follow
the identical StateGraph construction pattern. Core duplicated logic (~15 lines each):

```
1. Create StateGraph(ResearchState)
2. Optionally add split_document node
3. For each task: add_node(task, _make_generation_node(client, task))
4. add_node(render_name, render_fn)
5. Chain edges: START → [split →] tasks[0] → tasks[1] → ... → render_name → END
6. return graph.compile()
```

### Decision

Extract `_build_linear_graph()`:

```python
def _build_linear_graph(
    client: ResearchClient,
    tasks: list[str],
    render_name: str,
    render_fn: Callable[[ResearchState], dict[str, Any]],
    *,
    include_split: bool = False,
) -> CompiledStateGraph:
    graph: StateGraph = StateGraph(ResearchState)
    if include_split:
        graph.add_node("split_document", _split_document_node(client))
    for task in tasks:
        graph.add_node(task, _make_generation_node(client, task))
    graph.add_node(render_name, render_fn)

    first = tasks[0]
    if include_split:
        graph.add_edge(START, "split_document")
        graph.add_edge("split_document", first)
    else:
        graph.add_edge(START, first)
    for left, right in zip(tasks, tasks[1:]):
        graph.add_edge(left, right)
    graph.add_edge(tasks[-1], render_name)
    graph.add_edge(render_name, END)
    return graph.compile()
```

Public builders become single-line calls:

```python
def build_phase1_workflow(client: ResearchClient) -> CompiledStateGraph:
    return _build_linear_graph(
        client, PHASE1_TASKS, "render_analyst", _render_analyst_node, include_split=True
    )

def build_phase2_workflow(client: ResearchClient) -> CompiledStateGraph:
    return _build_linear_graph(client, PHASE2_TASKS, "render_document", _render_node)

def build_workflow(client: ResearchClient) -> CompiledStateGraph:
    return _build_linear_graph(
        client, PHASE1_TASKS + PHASE2_TASKS, "render_document", _render_node,
        include_split=True
    )
```

### Rationale

- Eliminates ~45 lines of duplicated graph construction
- Public function signatures are unchanged — callers are unaffected
- Adding a new workflow variant is a single `_build_linear_graph` call

### Alternatives Considered

- **Class-based workflow builder**: Rejected — overkill for 3 variants sharing a simple pattern
- **Keeping the 3 separate implementations**: Rejected — FR-004 violation

---

## R-3: Render Node Debate Output Deduplication

### Problem

`_render_node()` and `_render_analyst_node()` both duplicate the pattern:

```python
if state.get("debate_optimist"):
    opt_state = build_perspective_state(state, state["debate_optimist"])
    result["debate_optimist_analyst_markdown"] = render_analyst_markdown(opt_state)
    # _render_node also adds morning note and payload here
if state.get("debate_pessimist"):
    pes_state = build_perspective_state(state, state["debate_pessimist"])
    result["debate_pessimist_analyst_markdown"] = render_analyst_markdown(pes_state)
```

### Decision

Extract `_add_debate_perspective_outputs(state, result, *, with_morning_note)`:

```python
def _add_debate_perspective_outputs(
    state: ResearchState,
    result: dict[str, Any],
    *,
    with_morning_note: bool,
) -> None:
    for perspective_key, prefix in [
        ("debate_optimist", "debate_optimist"),
        ("debate_pessimist", "debate_pessimist"),
    ]:
        perspective = state.get(perspective_key)
        if perspective:
            pstate = build_perspective_state(state, perspective)
            result[f"{prefix}_analyst_markdown"] = render_analyst_markdown(pstate)
            if with_morning_note:
                result[f"{prefix}_morning_note_markdown"] = render_morning_note_markdown(pstate)
                result[f"{prefix}_payload"] = build_payload(pstate)
```

---

## R-4: Renderer Header Deduplication

### Problem

`render_markdown()` (lines 89-154 of renderer.py) assembles the company/ticker/analyst/
model metadata block and timestamp independently instead of calling `_build_header()`.

### Decision

Replace the inline metadata assembly in `render_markdown()` with a call to
`_build_header(state)`.

---

## R-5: Type Annotation Gaps (Inventory)

### Gaps by file

| File | Gap | Fix |
|------|-----|-----|
| `llm.py` | `_llm` has no declared type; `_azure_client` has no declared type | Declare as `ChatOpenAI \| ChatAnthropic` and `AzureOpenAI` respectively |
| `llm.py` | `Optional[str]` import not needed with Python 3.11+ | Replace with `str \| None` |
| `workflow.py` | `_render_node` declared `-> ResearchState` but returns partial `dict` | Change to `-> dict[str, Any]` |
| `workflow.py` | `_render_analyst_node` returns `dict` | Change to `-> dict[str, Any]` |
| `workflow.py` | `_split_document_node` inner function returns `dict` | Add `-> dict[str, Any]` |
| `workflow.py` | `_make_generation_node` inner function returns `dict` | Add `-> dict[str, Any]` |
| `renderer.py` | `build_perspective_state` casts plain `dict` overlay to `ResearchState` | Use `cast(ResearchState, overlay)` from typing, or type as `ResearchState` directly |
| `storage.py` | `payload: dict \| None` | `dict[str, Any] \| None` |
| `web.py` | All route functions have no return type | `Response \| tuple[Response, int]` |
| `config.py` | `load_dotenv` at module level before class | Acceptable but move inside `__init__` or make conditional |

### mypy command

```bash
mypy src/equity_research_agent/ --ignore-missing-imports
```

All issues above must produce zero mypy errors/warnings after the refactor.

---

## R-6: Logging Strategy

### Decision

Use `logging.getLogger(__name__)` in `workflow.py`. Replace the bare `except Exception:
pass` in `_split_document_node` with:

```python
except Exception as exc:
    logger.warning("Document splitting failed, falling back to full text: %s", exc)
    return {"document_sections": None}
```

No other modules require new logging — the existing error propagation patterns
(raising `ValueError`, `KeyError`) are correct and should remain.

---

## R-7: Test Infrastructure Plan

### Mocking strategy

The `ResearchClient._call_provider` extraction (R-1) creates a clean mock boundary:

```python
# In test_llm.py:
with patch.object(client, "_call_provider", return_value="mocked output") as mock_call:
    result = client.generate("summary_bullets", state)
    assert result == "mocked output"
    mock_call.assert_called_once()
```

For workflow tests, mock `ResearchClient` entirely:

```python
mock_client = MagicMock(spec=ResearchClient)
mock_client.debate_enabled = False
mock_client.generate.return_value = "generated text"
```

For web tests, use Flask's `app.test_client()` with patched `ResearchClient` and
`build_phase1_workflow`.

### New test files

| File | What it tests |
|------|---------------|
| `test_llm.py` | `ResearchClient.__init__` for each provider; `generate()`; `generate_with_debate()`; `_call_provider` dispatch; unknown task key raises `KeyError`; unknown provider raises `ValueError` |
| `test_workflow.py` | `_parse_document_sections()`; `_make_generation_node()`; `_split_document_node()` including exception fallback + logging; `_build_linear_graph()`; `build_phase1_workflow()`, `build_phase2_workflow()`, `build_workflow()` compilation |
| `test_cli.py` | `_parse_args()`; `_load_input_text()` with file / inline text / stdin; `main()` with mocked workflow and store |
| `test_web.py` | `POST /api/run` happy path + missing input; `GET /api/status/` known + unknown job; `POST /api/approve/` approve + reject; `POST /api/feedback/`; `GET /api/history`; `GET /api/history/<run_id>` |
