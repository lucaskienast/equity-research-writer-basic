from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from .llm import ResearchClient
from .models import ResearchState
from .renderer import build_payload, build_perspective_state, render_markdown, render_analyst_markdown, render_morning_note_markdown, render_document_sections_markdown

logger = logging.getLogger(__name__)

_SECTION_RE = re.compile(r'\[SECTION:\s*([A-Z_]+)\]', re.MULTILINE)

_SPLIT_CHAR_THRESHOLD = 12_000  # ~3,000 tokens


def _parse_document_sections(text: str) -> dict[str, str]:
    parts = _SECTION_RE.split(text)
    # parts alternates: [preamble, name1, body1, name2, body2, ...]
    sections: dict[str, str] = {}
    it = iter(parts[1:])  # skip preamble
    for name, body in zip(it, it):
        sections[name.strip()] = body.strip()
    return sections


def _split_document_node(client: ResearchClient) -> Callable[[ResearchState], dict[str, Any]]:
    def _node(state: ResearchState) -> dict[str, Any]:
        raw = state.get("raw_input", "")
        if len(raw) < _SPLIT_CHAR_THRESHOLD:
            return {"document_sections": None}
        try:
            output = client.generate("split_document", state)
            sections = _parse_document_sections(output)
            if len(sections) < 2:
                return {"document_sections": None}
            return {"document_sections": sections}
        except Exception as exc:
            logger.warning("Document splitting failed, falling back to full text: %s", exc)
            return {"document_sections": None}

    return _node


def _make_generation_node(client: ResearchClient, task_key: str) -> Callable[[ResearchState], dict[str, Any]]:
    def _node(state: ResearchState) -> dict[str, Any]:
        if client.debate_enabled:
            judge, optimist, pessimist = client.generate_with_debate(task_key, state)
            return {
                task_key: judge,
                "debate_optimist": {task_key: optimist},
                "debate_pessimist": {task_key: pessimist},
            }
        return {task_key: client.generate(task_key, state)}

    return _node


def _add_debate_perspective_outputs(
    state: ResearchState,
    result: dict[str, Any],
    *,
    with_morning_note: bool,
) -> None:
    for perspective_key, prefix in [
        ("debate_optimist", "debate_optimist"),
        ("debate_pessimist", "debate_pessimist"),
    ]:
        perspective = state.get(perspective_key)
        if perspective:
            pstate = build_perspective_state(state, perspective)  # type: ignore[arg-type]
            result[f"{prefix}_analyst_markdown"] = render_analyst_markdown(pstate)
            if with_morning_note:
                result[f"{prefix}_morning_note_markdown"] = render_morning_note_markdown(pstate)
                result[f"{prefix}_payload"] = build_payload(pstate)


def _render_node(state: ResearchState) -> dict[str, Any]:
    markdown = render_markdown(state)
    payload = build_payload(state)
    analyst_md = render_analyst_markdown(state)
    morning_note_md = render_morning_note_markdown(state)
    sections_md = render_document_sections_markdown(state)
    result: dict[str, Any] = {
        "final_markdown": markdown,
        "final_payload": payload,
        "final_analyst_markdown": analyst_md,
        "final_morning_note_markdown": morning_note_md,
        "final_document_sections_markdown": sections_md,
    }
    _add_debate_perspective_outputs(state, result, with_morning_note=True)
    return result


PHASE1_TASKS = ["summary_bullets", "unobvious_points", "spark"]
PHASE2_TASKS = ["financials", "commercial", "segments", "outlook", "top_bullets", "executive_summary", "title"]


def _render_analyst_node(state: ResearchState) -> dict[str, Any]:
    from .renderer import render_analyst_markdown
    result: dict[str, Any] = {"final_analyst_markdown": render_analyst_markdown(state)}
    _add_debate_perspective_outputs(state, result, with_morning_note=False)
    return result


def _build_linear_graph(
    client: ResearchClient,
    tasks: list[str],
    render_name: str,
    render_fn: Callable[[ResearchState], dict[str, Any]],
    *,
    include_split: bool = False,
) -> Any:  # returns CompiledStateGraph
    graph: StateGraph = StateGraph(ResearchState)
    if include_split:
        graph.add_node("split_document", _split_document_node(client))  # type: ignore[call-overload]
    for task in tasks:
        graph.add_node(task, _make_generation_node(client, task))  # type: ignore[call-overload]
    graph.add_node(render_name, render_fn)  # type: ignore[call-overload]

    first = tasks[0]
    if include_split:
        graph.add_edge(START, "split_document")
        graph.add_edge("split_document", first)
    else:
        graph.add_edge(START, first)
    for left, right in zip(tasks, tasks[1:]):
        graph.add_edge(left, right)
    graph.add_edge(tasks[-1], render_name)
    graph.add_edge(render_name, END)
    return graph.compile()


def build_phase1_workflow(client: ResearchClient) -> Any:
    return _build_linear_graph(
        client, PHASE1_TASKS, "render_analyst", _render_analyst_node, include_split=True
    )


def build_phase2_workflow(client: ResearchClient) -> Any:
    return _build_linear_graph(client, PHASE2_TASKS, "render_document", _render_node)


def build_workflow(client: ResearchClient) -> Any:
    return _build_linear_graph(
        client,
        PHASE1_TASKS + PHASE2_TASKS,
        "render_document",
        _render_node,
        include_split=True,
    )
