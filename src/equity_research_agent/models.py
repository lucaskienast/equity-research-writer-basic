from __future__ import annotations

from typing import Any

from typing_extensions import TypedDict


class ResearchState(TypedDict, total=False):
    raw_input: str
    company: str | None
    ticker: str | None
    analyst: str | None
    summary_bullets: str
    unobvious_points: str
    spark: str
    financials: str
    commercial: str
    segments: str
    outlook: str
    top_bullets: str
    executive_summary: str
    title: str
    document_sections: dict[str, str] | None
    llm_model: str
    final_markdown: str
    final_payload: dict[str, Any]
    final_analyst_markdown: str
    final_morning_note_markdown: str
    final_document_sections_markdown: str | None
