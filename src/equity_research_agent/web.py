from __future__ import annotations

import threading
import uuid
from io import BytesIO

import pdfplumber
from flask import Flask, jsonify, render_template, request

from .config import Settings
from .llm import ResearchClient
from .storage import ArtifactStore
from .workflow import build_workflow

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB

_jobs: dict[str, dict] = {}


def _run_worker(job_id: str, raw_input: str, company: str | None, ticker: str | None, analyst: str | None) -> None:
    try:
        settings = Settings()
        client = ResearchClient(settings)
        workflow = build_workflow(client)
        state = workflow.invoke(
            {
                "raw_input": raw_input,
                "company": company or None,
                "ticker": ticker or None,
                "analyst": analyst or None,
                "llm_model": settings.llm_model,
            }
        )
        store = ArtifactStore(settings)
        store.save_local(
            title=state["title"],
            analyst_markdown=state["final_analyst_markdown"],
            morning_note_markdown=state["final_morning_note_markdown"],
            payload=state["final_payload"],
            document_sections_markdown=state.get("final_document_sections_markdown"),
        )
        _jobs[job_id] = {
            "status": "done",
            "analyst_markdown": state.get("final_analyst_markdown"),
            "morning_note_markdown": state.get("final_morning_note_markdown"),
            "title": state.get("title"),
            "error": None,
        }
    except Exception as exc:
        _jobs[job_id] = {
            "status": "error",
            "analyst_markdown": None,
            "morning_note_markdown": None,
            "title": None,
            "error": str(exc),
        }


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
        "error": None,
    }

    thread = threading.Thread(target=_run_worker, args=(job_id, raw_input, company, ticker, analyst), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id}), 202


@app.route("/api/status/<job_id>")
def api_status(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        return jsonify({"error": "Job not found."}), 404
    return jsonify(job)


@app.errorhandler(413)
def request_entity_too_large(e):
    return jsonify({"error": "File too large. Maximum size is 20 MB."}), 413


if __name__ == "__main__":
    app.run(debug=True, port=5000)
