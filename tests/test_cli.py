from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from equity_research_agent.cli import _load_input_text, _parse_args


def test_parse_args_text():
    with patch("sys.argv", ["cli", "--text", "hello world", "--company", "Acme"]):
        args = _parse_args()
    assert args.text == "hello world"
    assert args.company == "Acme"


def test_load_input_text_from_text_arg(tmp_path):
    with patch("sys.argv", ["cli", "--text", "inline text"]):
        args = _parse_args()
    result = _load_input_text(args)
    assert result == "inline text"


def test_load_input_text_from_txt_file(tmp_path):
    f = tmp_path / "input.txt"
    f.write_text("file content", encoding="utf-8")
    with patch("sys.argv", ["cli", "--input-file", str(f)]):
        args = _parse_args()
    result = _load_input_text(args)
    assert result == "file content"


def test_load_input_text_no_input_raises(monkeypatch):
    monkeypatch.setattr("sys.stdin", MagicMock(isatty=lambda: True))
    with patch("sys.argv", ["cli"]):
        args = _parse_args()
    with pytest.raises(ValueError, match="Provide"):
        _load_input_text(args)


def test_main_runs_without_error(tmp_path):
    from equity_research_agent.cli import main

    fake_state = {
        "title": "Test Title",
        "final_markdown": "# Test",
        "final_analyst_markdown": "# Analyst",
        "final_morning_note_markdown": "# Morning",
        "final_payload": {"title": "Test Title"},
        "final_document_sections_markdown": None,
        "debate_optimist_analyst_markdown": None,
        "debate_optimist_morning_note_markdown": None,
        "debate_optimist_payload": None,
        "debate_pessimist_analyst_markdown": None,
        "debate_pessimist_morning_note_markdown": None,
        "debate_pessimist_payload": None,
    }
    mock_workflow = MagicMock()
    mock_workflow.invoke.return_value = fake_state

    from equity_research_agent.storage import PersistedArtifacts

    mock_persisted = PersistedArtifacts(
        run_dir=tmp_path,
        analyst_markdown_path=tmp_path / "analyst_review.md",
        morning_note_markdown_path=tmp_path / "morning_note.md",
        json_path=tmp_path / "research_note.json",
    )

    with (
        patch("sys.argv", ["cli", "--text", "Revenue up 10%.", "--company", "Test Co"]),
        patch("equity_research_agent.cli.ResearchClient"),
        patch("equity_research_agent.cli.build_workflow", return_value=mock_workflow),
        patch("equity_research_agent.cli.ArtifactStore") as mock_store_cls,
    ):
        mock_store_cls.return_value.save_local.return_value = mock_persisted
        main()
