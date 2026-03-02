from __future__ import annotations

from typing import Callable

from langgraph.graph import END, START, StateGraph

from .llm import ClaudeResearchClient
from .models import ResearchState
from .renderer import build_payload, render_markdown


def _make_generation_node(client: ClaudeResearchClient, task_key: str) -> Callable[[ResearchState], ResearchState]:
    def _node(state: ResearchState) -> ResearchState:
        return {task_key: client.generate(task_key, state)}

    return _node


def _render_node(state: ResearchState) -> ResearchState:
    markdown = render_markdown(state)
    payload = build_payload(state)
    return {"final_markdown": markdown, "final_payload": payload}


def build_workflow(client: ClaudeResearchClient):
    graph = StateGraph(ResearchState)

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

    graph.add_edge(START, ordered_tasks[0])
    for left, right in zip(ordered_tasks, ordered_tasks[1:]):
        graph.add_edge(left, right)
    graph.add_edge(ordered_tasks[-1], "render_document")
    graph.add_edge("render_document", END)

    return graph.compile()
