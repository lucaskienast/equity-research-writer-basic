# Web API Contracts

**Feature**: `001-clean-refactor`
**Date**: 2026-03-27

These contracts describe the Flask web API exposed by `web.py`. The refactor does not
change any endpoint paths, request formats, or response schemas. This document records
the authoritative contract for test coverage and future extension.

---

## POST /api/run

Accepts a research request, starts Phase 1 as a background job, and returns a job ID.

**Request** (multipart/form-data):

| Field | Type | Required | Description |
|---|---|---|---|
| `text` | string | No | Raw inline text to analyse |
| `file` | file | No | PDF or TXT document (max 20 MB) |
| `company` | string | No | Company name metadata |
| `ticker` | string | No | Ticker symbol metadata |
| `analyst` | string | No | Requesting analyst metadata |

At least one of `text` or `file` must be non-empty.

**Response 202**:

```json
{ "job_id": "<uuid>" }
```

**Response 400**:

```json
{ "error": "No input text provided." }
{ "error": "Only .pdf and .txt files are supported." }
```

**Response 413** (file too large):

```json
{ "error": "File too large. Maximum size is 20 MB." }
```

---

## GET /api/status/\<job_id\>

Returns the current status and any available outputs for a job.

**Response 200** (public fields — fields starting with `_` are excluded):

```json
{
  "status": "running | awaiting_approval | phase2_running | done | error | cancelled",
  "analyst_markdown": "<markdown string or null>",
  "morning_note_markdown": "<markdown string or null>",
  "optimist_analyst_markdown": "<markdown string or null>",
  "pessimist_analyst_markdown": "<markdown string or null>",
  "optimist_morning_note_markdown": "<markdown string or null>",
  "pessimist_morning_note_markdown": "<markdown string or null>",
  "title": "<string or null>",
  "run_dir": "<path string or null>",
  "error": "<string or null>"
}
```

**Response 404**:

```json
{ "error": "Job not found." }
```

---

## POST /api/approve/\<job_id\>

Approves or rejects a Phase 1 result. If approved, starts Phase 2. If rejected,
cancels the job.

**Request** (application/json):

```json
{ "approved": true }
```

**Response 200**:

```json
{ "ok": true }
```

**Response 404**:

```json
{ "error": "Job not found." }
```

**Response 409** (job not in `awaiting_approval` state):

```json
{ "error": "Job is not awaiting approval." }
```

---

## POST /api/feedback/\<job_id\>

Submits a rating and optional critique for a completed job. Written to
`{run_dir}/feedback.json`.

**Request** (application/json):

```json
{
  "rating": 4,
  "critique": "Good summary but missed the margin compression detail."
}
```

| Field | Type | Required | Constraint |
|---|---|---|---|
| `rating` | integer | Yes | 1–5 inclusive |
| `critique` | string | No | Free text |

**Response 200**:

```json
{ "ok": true }
```

**Response 400**:

```json
{ "error": "rating must be an integer 1–5." }
```

**Response 404** (job not found or not complete):

```json
{ "error": "Job not found or not complete." }
```

---

## GET /api/history

Returns a list of completed runs from the local output directory, sorted newest first.
Only directories containing a `research_note.json` file are included.

**Response 200**:

```json
[
  {
    "run_id": "20260327T101500Z-acme-demand-slows",
    "company": "Acme Corp",
    "ticker": "ACM",
    "title": "Demand Slows, Margins Hold",
    "date": "27/03/2026"
  }
]
```

---

## GET /api/history/\<run_id\>

Returns the full content for a specific historical run.

**Path validation**: `run_id` must match `^[\w\-]+$` to prevent path traversal.

**Response 200**:

```json
{
  "analyst_markdown": "<string>",
  "morning_note_markdown": "<string>",
  "optimist_analyst_markdown": "<string or null>",
  "pessimist_analyst_markdown": "<string or null>",
  "optimist_morning_note_markdown": "<string or null>",
  "pessimist_morning_note_markdown": "<string or null>",
  "title": "<string>",
  "company": "<string>",
  "ticker": "<string>",
  "feedback": { "rating": 4, "critique": "...", "submitted_at": "..." } | null
}
```

**Response 400** (invalid run_id format):

```json
{ "error": "Invalid run_id." }
```

**Response 404**:

```json
{ "error": "Run not found." }
```

---

## GET /

Serves the web UI HTML template (`templates/index.html`). No change.
