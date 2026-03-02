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
    final_markdown: str
    final_payload: dict[str, Any]
