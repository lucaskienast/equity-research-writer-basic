from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import Settings


@dataclass(slots=True)
class PersistedArtifacts:
    run_dir: Path
    analyst_markdown_path: Path | None = None
    morning_note_markdown_path: Path | None = None
    json_path: Path | None = None
    document_sections_path: Path | None = None
    source_input_path: Path | None = None
    source_file_path: Path | None = None
    optimist_analyst_path: Path | None = None
    optimist_morning_note_path: Path | None = None
    optimist_json_path: Path | None = None
    pessimist_analyst_path: Path | None = None
    pessimist_morning_note_path: Path | None = None
    pessimist_json_path: Path | None = None
    sharepoint_urls: dict[str, str] | None = None


def _simple_slugify(value: str) -> str:
    normalised = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", normalised).strip("-").lower()
    return cleaned or "research-note"


class ArtifactStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def save_local(
        self,
        title: str,
        analyst_markdown: str | None = None,
        morning_note_markdown: str | None = None,
        payload: dict[str, Any] | None = None,
        document_sections_markdown: str | None = None,
        raw_input_text: str | None = None,
        source_file_bytes: bytes | None = None,
        source_file_name: str | None = None,
        optimist_analyst_markdown: str | None = None,
        optimist_morning_note_markdown: str | None = None,
        optimist_payload: dict[str, Any] | None = None,
        pessimist_analyst_markdown: str | None = None,
        pessimist_morning_note_markdown: str | None = None,
        pessimist_payload: dict[str, Any] | None = None,
        run_dir: Path | None = None,
    ) -> PersistedArtifacts:
        if run_dir is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            slug = _simple_slugify(title)[:60]
            run_dir = self.settings.local_output_dir / f"{timestamp}-{slug}"
        run_dir.mkdir(parents=True, exist_ok=True)

        # Source inputs
        source_input_path: Path | None = None
        if raw_input_text:
            source_input_path = run_dir / "source_input.txt"
            source_input_path.write_text(raw_input_text, encoding="utf-8")

        source_file_path: Path | None = None
        if source_file_bytes:
            ext = Path(source_file_name).suffix if source_file_name else ".bin"
            source_file_path = run_dir / f"source_document{ext}"
            source_file_path.write_bytes(source_file_bytes)

        # Core artifacts
        analyst_markdown_path: Path | None = None
        if analyst_markdown:
            analyst_markdown_path = run_dir / "analyst_review.md"
            analyst_markdown_path.write_text(analyst_markdown, encoding="utf-8")

        morning_note_markdown_path: Path | None = None
        if morning_note_markdown:
            morning_note_markdown_path = run_dir / "morning_note.md"
            morning_note_markdown_path.write_text(morning_note_markdown, encoding="utf-8")

        json_path: Path | None = None
        if payload:
            json_path = run_dir / "research_note.json"
            json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        document_sections_path: Path | None = None
        if document_sections_markdown:
            document_sections_path = run_dir / "document_sections.md"
            document_sections_path.write_text(document_sections_markdown, encoding="utf-8")

        # Debate perspective artifacts
        optimist_analyst_path: Path | None = None
        optimist_morning_note_path: Path | None = None
        optimist_json_path: Path | None = None
        if optimist_analyst_markdown:
            optimist_analyst_path = run_dir / "analyst_review_optimist.md"
            optimist_analyst_path.write_text(optimist_analyst_markdown, encoding="utf-8")
        if optimist_morning_note_markdown:
            optimist_morning_note_path = run_dir / "morning_note_optimist.md"
            optimist_morning_note_path.write_text(optimist_morning_note_markdown, encoding="utf-8")
        if optimist_payload:
            optimist_json_path = run_dir / "research_note_optimist.json"
            optimist_json_path.write_text(json.dumps(optimist_payload, indent=2, ensure_ascii=False), encoding="utf-8")

        pessimist_analyst_path: Path | None = None
        pessimist_morning_note_path: Path | None = None
        pessimist_json_path: Path | None = None
        if pessimist_analyst_markdown:
            pessimist_analyst_path = run_dir / "analyst_review_pessimist.md"
            pessimist_analyst_path.write_text(pessimist_analyst_markdown, encoding="utf-8")
        if pessimist_morning_note_markdown:
            pessimist_morning_note_path = run_dir / "morning_note_pessimist.md"
            pessimist_morning_note_path.write_text(pessimist_morning_note_markdown, encoding="utf-8")
        if pessimist_payload:
            pessimist_json_path = run_dir / "research_note_pessimist.json"
            pessimist_json_path.write_text(json.dumps(pessimist_payload, indent=2, ensure_ascii=False), encoding="utf-8")

        return PersistedArtifacts(
            run_dir=run_dir,
            analyst_markdown_path=analyst_markdown_path,
            morning_note_markdown_path=morning_note_markdown_path,
            json_path=json_path,
            document_sections_path=document_sections_path,
            source_input_path=source_input_path,
            source_file_path=source_file_path,
            optimist_analyst_path=optimist_analyst_path,
            optimist_morning_note_path=optimist_morning_note_path,
            optimist_json_path=optimist_json_path,
            pessimist_analyst_path=pessimist_analyst_path,
            pessimist_morning_note_path=pessimist_morning_note_path,
            pessimist_json_path=pessimist_json_path,
        )

    def upload(self, persisted: PersistedArtifacts) -> dict[str, str]:
        from .sharepoint import SharePointUploader

        self.settings.validate_for_upload()
        uploader = SharePointUploader(self.settings)
        urls = uploader.upload(persisted)
        persisted.sharepoint_urls = urls
        return urls
