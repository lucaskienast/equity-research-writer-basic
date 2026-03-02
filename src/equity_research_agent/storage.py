from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import Settings


@dataclass(slots=True)
class PersistedArtifacts:
    run_dir: Path
    markdown_path: Path
    json_path: Path
    azure_urls: dict[str, str] | None = None


def _simple_slugify(value: str) -> str:
    normalised = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", normalised).strip("-").lower()
    return cleaned or "research-note"


class ArtifactStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def save_local(self, title: str, markdown: str, payload: dict) -> PersistedArtifacts:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        slug = _simple_slugify(title)[:60]
        run_dir = self.settings.local_output_dir / f"{timestamp}-{slug}"
        run_dir.mkdir(parents=True, exist_ok=True)

        markdown_path = run_dir / "research_note.md"
        json_path = run_dir / "research_note.json"

        markdown_path.write_text(markdown, encoding="utf-8")
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        return PersistedArtifacts(run_dir=run_dir, markdown_path=markdown_path, json_path=json_path)

    def upload(self, persisted: PersistedArtifacts) -> dict[str, str]:
        from azure.core.exceptions import ResourceExistsError
        from azure.storage.blob import BlobServiceClient, ContentSettings

        self.settings.validate_for_upload()
        timestamp = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        prefix = self.settings.azure_blob_prefix.strip("/")

        service = BlobServiceClient.from_connection_string(self.settings.azure_storage_connection_string)
        container = service.get_container_client(self.settings.azure_blob_container)
        try:
            container.create_container()
        except ResourceExistsError:
            pass

        uploads: dict[str, str] = {}
        for label, path, content_type in [
            ("markdown", persisted.markdown_path, "text/markdown"),
            ("json", persisted.json_path, "application/json"),
        ]:
            blob_name = f"{prefix}/{timestamp}/{persisted.run_dir.name}/{path.name}"
            blob_client = container.get_blob_client(blob_name)
            with path.open("rb") as fh:
                blob_client.upload_blob(
                    fh,
                    overwrite=True,
                    content_settings=ContentSettings(content_type=content_type),
                )
            uploads[label] = blob_client.url

        persisted.azure_urls = uploads
        return uploads
