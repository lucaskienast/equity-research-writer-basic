from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import ResearchState


def render_markdown(state: ResearchState) -> str:
    company_line = []
    if state.get("company"):
        company_line.append(f"**Company:** {state['company']}")
    if state.get("ticker"):
        company_line.append(f"**Ticker:** {state['ticker']}")
    if state.get("analyst"):
        company_line.append(f"**Requested by:** {state['analyst']}")

    metadata_block = " | ".join(company_line)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    sections = [
        f"# {state['title']}",
        metadata_block if metadata_block else "",
        f"**Generated:** {generated_at}",
        "",
        "## Top bullets",
        state["top_bullets"],
        "",
        "## Summary paragraph",
        state["executive_summary"],
        "",
        "## High-level summary bullets",
        state["summary_bullets"],
        "",
        "## Unobvious points",
        state["unobvious_points"],
        "",
        "## The Spark",
        state["spark"],
        "",
        "## The Financials",
        state["financials"],
        "",
        "## The Commercial",
        state["commercial"],
        "",
        "## The Segments",
        state["segments"],
        "",
        "## The Outlook",
        state["outlook"],
    ]
    return "\n".join(part for part in sections if part is not None).strip() + "\n"


def build_payload(state: ResearchState) -> dict[str, Any]:
    return {
        "title": state["title"],
        "company": state.get("company"),
        "ticker": state.get("ticker"),
        "analyst": state.get("analyst"),
        "summary_bullets": state["summary_bullets"],
        "unobvious_points": state["unobvious_points"],
        "spark": state["spark"],
        "financials": state["financials"],
        "commercial": state["commercial"],
        "segments": state["segments"],
        "outlook": state["outlook"],
        "top_bullets": state["top_bullets"],
        "executive_summary": state["executive_summary"],
        "raw_input": state["raw_input"],
    }
