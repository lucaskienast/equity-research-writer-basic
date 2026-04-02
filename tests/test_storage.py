from pathlib import Path
from unittest.mock import patch

import pytest

from equity_research_agent.config import Settings
from equity_research_agent.storage import ArtifactStore, _simple_slugify


def test_save_local_writes_markdown_and_json(tmp_path: Path):
    settings = Settings(LOCAL_OUTPUT_DIR=tmp_path)
    store = ArtifactStore(settings)

    persisted = store.save_local(
        title="Demand improves, margins stabilise",
        analyst_markdown="# Analyst Review\n",
        morning_note_markdown="# Morning Note\n",
        payload={"title": "Demand improves, margins stabilise"},
    )

    assert persisted.run_dir.exists()
    assert persisted.analyst_markdown_path.exists()
    assert persisted.morning_note_markdown_path.exists()
    assert persisted.json_path.exists()
    assert persisted.analyst_markdown_path.read_text(encoding="utf-8") == "# Analyst Review\n"
    assert persisted.morning_note_markdown_path.read_text(encoding="utf-8") == "# Morning Note\n"


def test_simple_slugify_special_chars():
    assert _simple_slugify("Hello, World!") == "hello-world"
    assert _simple_slugify("") == "research-note"
    assert _simple_slugify("Acme Corp: Q1 Results") == "acme-corp-q1-results"


def test_save_local_with_explicit_run_dir(tmp_path):
    settings = Settings(LOCAL_OUTPUT_DIR=tmp_path)
    store = ArtifactStore(settings)
    run_dir = tmp_path / "my-run"
    persisted = store.save_local(
        title="Test",
        analyst_markdown="# Test",
        run_dir=run_dir,
    )
    assert persisted.run_dir == run_dir
    assert persisted.analyst_markdown_path is not None
    assert persisted.analyst_markdown_path.exists()


def test_save_local_debate_artifacts(tmp_path):
    settings = Settings(LOCAL_OUTPUT_DIR=tmp_path)
    store = ArtifactStore(settings)
    persisted = store.save_local(
        title="Test",
        analyst_markdown="# Analyst",
        morning_note_markdown="# Morning",
        payload={"title": "Test"},
        optimist_analyst_markdown="# Optimist",
        pessimist_analyst_markdown="# Pessimist",
        optimist_morning_note_markdown="# Opt Morning",
        pessimist_morning_note_markdown="# Pes Morning",
        optimist_payload={"title": "Opt"},
        pessimist_payload={"title": "Pes"},
    )
    assert persisted.optimist_analyst_path is not None
    assert persisted.optimist_analyst_path.exists()
    assert persisted.pessimist_analyst_path is not None
    assert persisted.pessimist_analyst_path.exists()


def test_save_local_source_file_bytes(tmp_path):
    settings = Settings(LOCAL_OUTPUT_DIR=tmp_path)
    store = ArtifactStore(settings)
    persisted = store.save_local(
        title="Test",
        source_file_bytes=b"fake pdf content",
        source_file_name="doc.pdf",
    )
    assert persisted.source_file_path is not None
    assert persisted.source_file_path.exists()
    assert persisted.source_file_path.read_bytes() == b"fake pdf content"


# ---------------------------------------------------------------------------
# T017 — sharepoint_urls field and ArtifactStore.upload() integration
# ---------------------------------------------------------------------------


def test_sharepoint_urls_field_exists(tmp_path: Path) -> None:
    settings = Settings(LOCAL_OUTPUT_DIR=tmp_path)
    store = ArtifactStore(settings)
    persisted = store.save_local(title="Test", analyst_markdown="# Test")
    assert persisted.sharepoint_urls is None


def test_upload_sets_sharepoint_urls(tmp_path: Path) -> None:
    settings = Settings(
        LOCAL_OUTPUT_DIR=tmp_path,
        SHAREPOINT_TENANT_ID="tid",
        SHAREPOINT_CLIENT_ID="cid",
        SHAREPOINT_CLIENT_SECRET="sec",
        SHAREPOINT_DRIVE_ID="did",
        UPLOAD_TO_SHAREPOINT=True,
    )
    store = ArtifactStore(settings)
    persisted = store.save_local(title="Test", analyst_markdown="# Test")

    mock_urls = {"analyst_markdown": "https://tenant.sharepoint.com/analyst_review.md"}

    with patch("equity_research_agent.sharepoint.SharePointUploader") as MockUploader:
        MockUploader.return_value.upload.return_value = mock_urls
        result = store.upload(persisted)

    assert result == mock_urls
    assert persisted.sharepoint_urls == mock_urls


# ---------------------------------------------------------------------------
# T028 — local files survive upload failure (FR-004 / SC-003)
# ---------------------------------------------------------------------------


def test_upload_failure_preserves_local_files(tmp_path: Path) -> None:
    settings = Settings(
        LOCAL_OUTPUT_DIR=tmp_path,
        SHAREPOINT_TENANT_ID="tid",
        SHAREPOINT_CLIENT_ID="cid",
        SHAREPOINT_CLIENT_SECRET="sec",
        SHAREPOINT_DRIVE_ID="did",
        UPLOAD_TO_SHAREPOINT=True,
    )
    store = ArtifactStore(settings)
    persisted = store.save_local(
        title="Test",
        analyst_markdown="# Analyst\n",
        morning_note_markdown="# Morning\n",
        payload={"title": "Test"},
    )

    assert persisted.analyst_markdown_path is not None
    assert persisted.analyst_markdown_path.exists()

    with patch("equity_research_agent.sharepoint.SharePointUploader") as MockUploader:
        MockUploader.return_value.upload.side_effect = RuntimeError("upload failed")
        with pytest.raises(RuntimeError, match="upload failed"):
            store.upload(persisted)

    # Local files must be untouched after upload failure
    assert persisted.analyst_markdown_path.exists()
    assert persisted.morning_note_markdown_path is not None
    assert persisted.morning_note_markdown_path.exists()
    assert persisted.json_path is not None
    assert persisted.json_path.exists()
    assert persisted.analyst_markdown_path.read_text(encoding="utf-8") == "# Analyst\n"
