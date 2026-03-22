from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import pdfplumber
from flask import Flask, jsonify, render_template, request

from .config import Settings
from .llm import ResearchClient
from .storage import ArtifactStore
from .workflow import build_workflow, build_phase1_workflow, build_phase2_workflow

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB

_jobs: dict[str, dict] = {}


def _public_job(job: dict) -> dict:
    return {k: v for k, v in job.items() if not k.startswith("_")}


def _run_phase1_worker(job_id: str, raw_input: str, company: str | None, ticker: str | None, analyst: str | None) -> None:
    try:
        settings = Settings()
        client = ResearchClient(settings)
        _jobs[job_id]["_client"] = client
        workflow = build_phase1_workflow(client)
        state = workflow.invoke(
            {
                "raw_input": raw_input,
                "company": company or None,
                "ticker": ticker or None,
                "analyst": analyst or None,
                "llm_model": settings.llm_model,
            }
        )
        _jobs[job_id]["status"] = "awaiting_approval"
        _jobs[job_id]["analyst_markdown"] = state.get("final_analyst_markdown")
        _jobs[job_id]["_state"] = state
    except Exception as exc:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(exc)
        _jobs[job_id]["_client"] = None
        _jobs[job_id]["_state"] = None


def _run_phase2_worker(job_id: str) -> None:
    job = _jobs[job_id]
    state = job["_state"]
    client = job["_client"]
    try:
        _jobs[job_id]["status"] = "phase2_running"
        workflow = build_phase2_workflow(client)
        state = workflow.invoke(state)
        settings = Settings()
        store = ArtifactStore(settings)
        persisted = store.save_local(
            title=state["title"],
            analyst_markdown=state["final_analyst_markdown"],
            morning_note_markdown=state["final_morning_note_markdown"],
            payload=state["final_payload"],
            document_sections_markdown=state.get("final_document_sections_markdown"),
        )
        _jobs[job_id]["status"] = "done"
        _jobs[job_id]["morning_note_markdown"] = state.get("final_morning_note_markdown")
        _jobs[job_id]["analyst_markdown"] = state.get("final_analyst_markdown")
        _jobs[job_id]["title"] = state.get("title")
        _jobs[job_id]["run_dir"] = str(persisted.run_dir)
        _jobs[job_id]["_state"] = None
        _jobs[job_id]["_client"] = None
    except Exception as exc:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(exc)
        _jobs[job_id]["_state"] = None
        _jobs[job_id]["_client"] = None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/run", methods=["POST"])
def api_run():
    file_text = ""
    uploaded = request.files.get("file")
    if uploaded and uploaded.filename:
        ext = uploaded.filename.rsplit(".", 1)[-1].lower() if "." in uploaded.filename else ""
        if ext not in ("pdf", "txt"):
            return jsonify({"error": "Only .pdf and .txt files are supported."}), 400
        data = uploaded.read()
        if ext == "pdf":
            with pdfplumber.open(BytesIO(data)) as pdf:
                file_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        else:
            file_text = data.decode("utf-8", errors="replace")

    typed_text = request.form.get("text", "").strip()

    if typed_text and file_text:
        raw_input = f"[User note]\n{typed_text}\n\n[Document: {uploaded.filename}]\n{file_text}"
    elif file_text:
        raw_input = file_text
    else:
        raw_input = typed_text

    if not raw_input.strip():
        return jsonify({"error": "No input text provided."}), 400

    company = request.form.get("company", "").strip() or None
    ticker = request.form.get("ticker", "").strip() or None
    analyst = request.form.get("analyst", "").strip() or None

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status": "running",
        "analyst_markdown": None,
        "morning_note_markdown": None,
        "title": None,
        "run_dir": None,
        "error": None,
        "_state": None,
        "_client": None,
    }

    thread = threading.Thread(target=_run_phase1_worker, args=(job_id, raw_input, company, ticker, analyst), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id}), 202


@app.route("/api/approve/<job_id>", methods=["POST"])
def api_approve(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        return jsonify({"error": "Job not found."}), 404
    if job.get("status") != "awaiting_approval":
        return jsonify({"error": "Job is not awaiting approval."}), 409

    data = request.get_json(force=True, silent=True) or {}
    approved = data.get("approved", False)

    if approved:
        thread = threading.Thread(target=_run_phase2_worker, args=(job_id,), daemon=True)
        thread.start()
    else:
        job["status"] = "cancelled"
        job["_state"] = None
        job["_client"] = None

    return jsonify({"ok": True})


@app.route("/api/feedback/<job_id>", methods=["POST"])
def api_feedback(job_id: str):
    job = _jobs.get(job_id)
    if job is None or job.get("status") != "done":
        return jsonify({"error": "Job not found or not complete."}), 404

    data = request.get_json(force=True, silent=True) or {}
    rating = data.get("rating")
    critique = data.get("critique", "").strip()

    if not isinstance(rating, int) or not (1 <= rating <= 5):
        return jsonify({"error": "rating must be an integer 1–5."}), 400

    run_dir = Path(job["run_dir"])
    feedback = {
        "rating": rating,
        "critique": critique or None,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }
    (run_dir / "feedback.json").write_text(
        json.dumps(feedback, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return jsonify({"ok": True})


@app.route("/api/status/<job_id>")
def api_status(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        return jsonify({"error": "Job not found."}), 404
    return jsonify(_public_job(job))


@app.route("/api/history")
def api_history():
    import re
    settings = Settings()
    output_dir = Path(settings.local_output_dir)
    if not output_dir.exists():
        return jsonify([])

    pattern = re.compile(r"^(\d{8}T\d{6}Z)-(.+)$")
    runs = []
    for d in output_dir.iterdir():
        if not d.is_dir():
            continue
        m = pattern.match(d.name)
        if not m:
            continue
        ts_str, _ = m.group(1), m.group(2)
        json_path = d / "research_note.json"
        if not json_path.exists():
            continue
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        # parse date: 20260320T160336Z → 20/03/2026
        date_fmt = f"{ts_str[6:8]}/{ts_str[4:6]}/{ts_str[0:4]}"
        runs.append({
            "run_id": d.name,
            "company": data.get("company") or "",
            "ticker": data.get("ticker") or "",
            "title": data.get("title") or "",
            "date": date_fmt,
            "_ts": ts_str,
        })

    runs.sort(key=lambda r: r["_ts"], reverse=True)
    for r in runs:
        del r["_ts"]
    return jsonify(runs)


@app.route("/api/history/<run_id>")
def api_history_run(run_id: str):
    import re
    # Prevent path traversal: only allow safe directory names
    if not re.match(r"^[\w\-]+$", run_id):
        return jsonify({"error": "Invalid run_id."}), 400

    settings = Settings()
    run_dir = Path(settings.local_output_dir) / run_id
    if not run_dir.is_dir():
        return jsonify({"error": "Run not found."}), 404

    analyst_md = (run_dir / "analyst_review.md").read_text(encoding="utf-8") if (run_dir / "analyst_review.md").exists() else ""
    morning_md = (run_dir / "morning_note.md").read_text(encoding="utf-8") if (run_dir / "morning_note.md").exists() else ""

    json_path = run_dir / "research_note.json"
    meta = {}
    if json_path.exists():
        try:
            meta = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    feedback = None
    feedback_path = run_dir / "feedback.json"
    if feedback_path.exists():
        try:
            feedback = json.loads(feedback_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    return jsonify({
        "analyst_markdown": analyst_md,
        "morning_note_markdown": morning_md,
        "title": meta.get("title") or "",
        "company": meta.get("company") or "",
        "ticker": meta.get("ticker") or "",
        "feedback": feedback,
    })


@app.errorhandler(413)
def request_entity_too_large(e):
    return jsonify({"error": "File too large. Maximum size is 20 MB."}), 413


if __name__ == "__main__":
    app.run(debug=True, port=5000)
