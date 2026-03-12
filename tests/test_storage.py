from pathlib import Path

from equity_research_agent.config import Settings
from equity_research_agent.storage import ArtifactStore


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
