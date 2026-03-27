from __future__ import annotations

from unittest.mock import patch

import pytest

from equity_research_agent.config import Settings
from equity_research_agent.llm import ResearchClient


def _minimal_state() -> dict:
    return {
        "raw_input": "Revenue up 10%. EBITDA £20m.",
        "company": "Test Co",
        "ticker": "TST",
        "analyst": "J. Smith",
    }


def test_unknown_provider_raises():
    settings = Settings(LLM_PROVIDER="unknown_provider", OPENAI_API_KEY="x")
    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
        ResearchClient(settings)


def test_generate_calls_call_provider(tmp_path):
    settings = Settings(LLM_PROVIDER="openai", OPENAI_API_KEY="fake")
    with patch("equity_research_agent.llm.ChatOpenAI"):
        client = ResearchClient(settings)
    with patch.object(client, "_call_provider", return_value="mocked output") as mock_call:
        result = client.generate("summary_bullets", _minimal_state())
    assert result == "mocked output"
    mock_call.assert_called_once()


def test_generate_unknown_task_key_raises(tmp_path):
    settings = Settings(LLM_PROVIDER="openai", OPENAI_API_KEY="fake")
    with patch("equity_research_agent.llm.ChatOpenAI"):
        client = ResearchClient(settings)
    with pytest.raises(KeyError, match="unknown_task"):
        client.generate("unknown_task", _minimal_state())


def test_generate_with_debate_returns_triple(tmp_path):
    settings = Settings(LLM_PROVIDER="openai", OPENAI_API_KEY="fake", ENABLE_DEBATE=True)
    with patch("equity_research_agent.llm.ChatOpenAI"):
        client = ResearchClient(settings)
    with patch.object(client, "_call_provider", return_value="output"):
        judge, optimist, pessimist = client.generate_with_debate("summary_bullets", _minimal_state())
    assert isinstance(judge, str)
    assert isinstance(optimist, str)
    assert isinstance(pessimist, str)


def test_normalise_response_text_string():
    assert ResearchClient._normalise_response_text("  hello  ") == "hello"


def test_normalise_response_text_list():
    result = ResearchClient._normalise_response_text(["hello", "world"])
    assert "hello" in result
    assert "world" in result


def test_normalise_response_text_non_string():
    result = ResearchClient._normalise_response_text(42)
    assert result == "42"
