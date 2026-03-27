from __future__ import annotations

from unittest.mock import MagicMock


from equity_research_agent.llm import ResearchClient
from equity_research_agent.workflow import (
    _build_linear_graph,
    _make_generation_node,
    _parse_document_sections,
    _split_document_node,
    build_phase1_workflow,
    build_phase2_workflow,
    build_workflow,
)


def _mock_client(debate: bool = False) -> MagicMock:
    client = MagicMock(spec=ResearchClient)
    client.debate_enabled = debate
    client.generate.return_value = "generated text"
    return client


def test_parse_document_sections_already_tested():
    # Covered by test_chunking.py — just verify import works
    assert callable(_parse_document_sections)


def test_build_linear_graph_compiles():
    client = _mock_client()
    graph = _build_linear_graph(client, ["summary_bullets"], "render_analyst", lambda s: {})
    assert graph is not None


def test_build_phase1_workflow_compiles():
    client = _mock_client()
    wf = build_phase1_workflow(client)
    assert wf is not None


def test_build_phase2_workflow_compiles():
    client = _mock_client()
    wf = build_phase2_workflow(client)
    assert wf is not None


def test_build_workflow_compiles():
    client = _mock_client()
    wf = build_workflow(client)
    assert wf is not None


def test_make_generation_node_calls_generate():
    client = _mock_client()
    state = {"raw_input": "test"}
    node = _make_generation_node(client, "summary_bullets")
    result = node(state)
    assert result == {"summary_bullets": "generated text"}
    client.generate.assert_called_once_with("summary_bullets", state)


def test_split_document_node_short_input():
    client = _mock_client()
    state = {"raw_input": "short text"}
    node = _split_document_node(client)
    result = node(state)
    assert result == {"document_sections": None}


def test_split_document_node_logs_warning_on_error(caplog):
    import logging
    client = _mock_client()
    client.generate.side_effect = RuntimeError("LLM failed")
    state = {"raw_input": "x" * 20000}  # long enough to trigger split attempt
    node = _split_document_node(client)
    with caplog.at_level(logging.WARNING, logger="equity_research_agent.workflow"):
        result = node(state)
    assert result == {"document_sections": None}
    assert any("splitting" in r.message.lower() or "failed" in r.message.lower() for r in caplog.records)
