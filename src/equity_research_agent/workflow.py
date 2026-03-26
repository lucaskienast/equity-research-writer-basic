from __future__ import annotations

import re
from typing import Callable

from langgraph.graph import END, START, StateGraph

from .llm import ResearchClient, ClaudeResearchClient
from .models import ResearchState
from .renderer import build_payload, build_perspective_state, render_markdown, render_analyst_markdown, render_morning_note_markdown, render_document_sections_markdown

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


def _split_document_node(client: ClaudeResearchClient) -> Callable[[ResearchState], ResearchState]:
    def _node(state: ResearchState) -> ResearchState:
        raw = state.get("raw_input", "")
        if len(raw) < _SPLIT_CHAR_THRESHOLD:
            return {"document_sections": None}
        try:
            output = client.generate("split_document", state)
            sections = _parse_document_sections(output)
            if len(sections) < 2:
                return {"document_sections": None}
            return {"document_sections": sections}
        except Exception:
            return {"document_sections": None}

    return _node


def _make_generation_node(client: ClaudeResearchClient, task_key: str) -> Callable[[ResearchState], ResearchState]:
    def _node(state: ResearchState) -> ResearchState:
        if client.debate_enabled:
            judge, optimist, pessimist = client.generate_with_debate(task_key, state)
            return {
                task_key: judge,
                "debate_optimist": {task_key: optimist},
                "debate_pessimist": {task_key: pessimist},
            }
        return {task_key: client.generate(task_key, state)}

    return _node


def _render_node(state: ResearchState) -> ResearchState:
    markdown = render_markdown(state)
    payload = build_payload(state)
    analyst_md = render_analyst_markdown(state)
    morning_note_md = render_morning_note_markdown(state)
    sections_md = render_document_sections_markdown(state)
    result: dict = {
        "final_markdown": markdown,
        "final_payload": payload,
        "final_analyst_markdown": analyst_md,
        "final_morning_note_markdown": morning_note_md,
        "final_document_sections_markdown": sections_md,
    }
    if state.get("debate_optimist"):
        opt_state = build_perspective_state(state, state["debate_optimist"])
        result["debate_optimist_analyst_markdown"] = render_analyst_markdown(opt_state)
        result["debate_optimist_morning_note_markdown"] = render_morning_note_markdown(opt_state)
        result["debate_optimist_payload"] = build_payload(opt_state)
    if state.get("debate_pessimist"):
        pes_state = build_perspective_state(state, state["debate_pessimist"])
        result["debate_pessimist_analyst_markdown"] = render_analyst_markdown(pes_state)
        result["debate_pessimist_morning_note_markdown"] = render_morning_note_markdown(pes_state)
        result["debate_pessimist_payload"] = build_payload(pes_state)
    return result


PHASE1_TASKS = ["summary_bullets", "unobvious_points", "spark"]
PHASE2_TASKS = ["financials", "commercial", "segments", "outlook", "top_bullets", "executive_summary", "title"]


def _render_analyst_node(state: ResearchState) -> dict:
    from .renderer import render_analyst_markdown
    result: dict = {"final_analyst_markdown": render_analyst_markdown(state)}
    if state.get("debate_optimist"):
        opt_state = build_perspective_state(state, state["debate_optimist"])
        result["debate_optimist_analyst_markdown"] = render_analyst_markdown(opt_state)
    if state.get("debate_pessimist"):
        pes_state = build_perspective_state(state, state["debate_pessimist"])
        result["debate_pessimist_analyst_markdown"] = render_analyst_markdown(pes_state)
    return result


def build_phase1_workflow(client: ResearchClient):
    graph = StateGraph(ResearchState)
    graph.add_node("split_document", _split_document_node(client))
    for task in PHASE1_TASKS:
        graph.add_node(task, _make_generation_node(client, task))
    graph.add_node("render_analyst", _render_analyst_node)

    graph.add_edge(START, "split_document")
    graph.add_edge("split_document", PHASE1_TASKS[0])
    for left, right in zip(PHASE1_TASKS, PHASE1_TASKS[1:]):
        graph.add_edge(left, right)
    graph.add_edge(PHASE1_TASKS[-1], "render_analyst")
    graph.add_edge("render_analyst", END)

    return graph.compile()


def build_phase2_workflow(client: ResearchClient):
    graph = StateGraph(ResearchState)
    for task in PHASE2_TASKS:
        graph.add_node(task, _make_generation_node(client, task))
    graph.add_node("render_document", _render_node)

    graph.add_edge(START, PHASE2_TASKS[0])
    for left, right in zip(PHASE2_TASKS, PHASE2_TASKS[1:]):
        graph.add_edge(left, right)
    graph.add_edge(PHASE2_TASKS[-1], "render_document")
    graph.add_edge("render_document", END)

    return graph.compile()


def build_workflow(client: ResearchClient):
    graph = StateGraph(ResearchState)

    graph.add_node("split_document", _split_document_node(client))

    ordered_tasks = [
        "summary_bullets",
        "unobvious_points",
        "spark",
        "financials",
        "commercial",
        "segments",
        "outlook",
        "top_bullets",
        "executive_summary",
        "title",
    ]

    for task in ordered_tasks:
        graph.add_node(task, _make_generation_node(client, task))

    graph.add_node("render_document", _render_node)

    graph.add_edge(START, "split_document")
    graph.add_edge("split_document", ordered_tasks[0])
    for left, right in zip(ordered_tasks, ordered_tasks[1:]):
        graph.add_edge(left, right)
    graph.add_edge(ordered_tasks[-1], "render_document")
    graph.add_edge("render_document", END)

    return graph.compile()
