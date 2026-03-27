# Quickstart: Validating the Clean Code Refactor

**Feature**: `001-clean-refactor`
**Date**: 2026-03-27

This guide describes how to verify that the refactor is complete and correct.
All steps must pass before the feature is considered done.

---

## Prerequisites

```bash
pip install -e ".[dev]"
pip install mypy  # if not already installed
```

---

## Step 1: Linting — zero issues

```bash
ruff check .
```

Expected output: nothing (exit code 0). Any output is a failure.

---

## Step 2: Type checking — zero errors

```bash
mypy src/equity_research_agent/ --ignore-missing-imports
```

Expected output:

```
Success: no issues found in N source files
```

Zero errors, zero warnings. Any "error:" or "note:" lines indicate a failure.

---

## Step 3: Test suite — all pass, no live API calls

```bash
pytest
```

Expected: all tests pass. No `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or
`AZURE_API_KEY` environment variables are required.

To run with verbose output:

```bash
pytest -v
```

---

## Step 4: Duplication check — verify key removals

### 4a. Azure dispatch appears once

```bash
grep -n "chat.completions.create" src/equity_research_agent/llm.py | wc -l
```

Expected: `1` (only in `_call_provider`).

### 4b. No inline metadata block in render_markdown

```bash
grep -n "company_line" src/equity_research_agent/renderer.py
```

Expected: only appears in `_build_header()`, not in `render_markdown()`.

### 4c. Workflow builders are single-line delegations

```bash
grep -A 5 "def build_phase1_workflow" src/equity_research_agent/workflow.py
```

Expected: the function body is a single `return _build_linear_graph(...)` call.

---

## Step 5: Functional smoke test — CLI

Requires a valid `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in `.env`.

```bash
python -m equity_research_agent.cli \
  --text "Revenue up 10% YoY. EBITDA £20m. Outlook maintained." \
  --company "Example Co" \
  --ticker EXM \
  --analyst "J. Smith"
```

Expected: workflow completes, three artifact files written to `output/`, no errors.

---

## Step 6: Functional smoke test — Web UI

```bash
make run-web
# In a separate terminal:
curl -X POST http://localhost:5000/api/run \
  -F "text=Revenue up 10% YoY." \
  -F "company=Example Co"
# Returns: {"job_id": "<uuid>"}

curl http://localhost:5000/api/status/<job_id>
# Eventually returns status: "awaiting_approval"
```

---

## Step 7: No prompts changed

```bash
git diff HEAD -- src/equity_research_agent/prompts.py
```

Expected: no output (file unchanged).

---

## Checklist

- [ ] `ruff check .` exits 0
- [ ] `mypy src/equity_research_agent/ --ignore-missing-imports` — "Success: no issues found"
- [ ] `pytest` — all tests pass, no API keys required
- [ ] `chat.completions.create` appears exactly once in `llm.py`
- [ ] `render_markdown()` calls `_build_header()` (no inline metadata)
- [ ] `build_phase1_workflow()` is a single `return _build_linear_graph(...)` call
- [ ] CLI smoke test completes without error
- [ ] Web UI smoke test completes without error
- [ ] `prompts.py` has zero git diff
