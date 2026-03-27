from pathlib import Path

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
