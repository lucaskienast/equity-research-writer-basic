from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import ResearchState


def _build_header(state: ResearchState) -> str:
    company_line = []
    if state.get("company"):
        company_line.append(f"**Company:** {state['company']}")
    if state.get("ticker"):
        company_line.append(f"**Ticker:** {state['ticker']}")
    if state.get("analyst"):
        company_line.append(f"**Requested by:** {state['analyst']}")
    if state.get("llm_model"):
        company_line.append(f"**Model:** {state['llm_model']}")
    metadata_block = " | ".join(company_line)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts = []
    if metadata_block:
        parts.append(metadata_block)
    parts.append(f"**Generated:** {generated_at}")
    return "\n".join(parts)


def render_analyst_markdown(state: ResearchState) -> str:
    header = _build_header(state)
    body = "\n".join([
        '<div style="background-color: #fffde7; padding: 16px; border-radius: 8px; border: 1px solid #fff176; margin: 16px 0;">',
        "",
        "## For Analyst Review",
        "",
        "### High-level summary bullets",
        state["summary_bullets"],
        "",
        "### Unobvious points",
        state["unobvious_points"],
        "",
        "### The Spark",
        state["spark"],
        "</div>",
    ])
    return "\n\n".join([header, body]).strip() + "\n"


def render_morning_note_markdown(state: ResearchState) -> str:
    header = _build_header(state)
    now = datetime.now(timezone.utc)
    note_date = f"{now.day} {now.strftime('%B %Y')}"
    sections = [
        header,
        "# Morning Note",
        note_date,
        "",
        f"## {state.get('company', '')}",
        "\n".join([
            '<div style="background-color: #e8f5e9; padding: 16px; border-radius: 8px; border: 1px solid #a5d6a7; margin: 16px 0;">',
            "",
            f"### {state['title']}",
            "",
            state["top_bullets"],
            "",
            state["executive_summary"],
            "</div>",
        ]),
        "",
        "### The Financials",
        state["financials"],
        "",
        "### The Commercial",
        state["commercial"],
        "",
        "### The Segments",
        state["segments"],
        "",
        "### The Outlook",
        state["outlook"],
    ]
    return "\n".join(part for part in sections if part is not None).strip() + "\n"


def render_markdown(state: ResearchState) -> str:
    company_line = []
    if state.get("company"):
        company_line.append(f"**Company:** {state['company']}")
    if state.get("ticker"):
        company_line.append(f"**Ticker:** {state['ticker']}")
    if state.get("analyst"):
        company_line.append(f"**Requested by:** {state['analyst']}")
    if state.get("llm_model"):
        company_line.append(f"**Model:** {state['llm_model']}")

    metadata_block = " | ".join(company_line)
    now = datetime.now(timezone.utc)
    generated_at = now.strftime("%Y-%m-%d %H:%M UTC")
    note_date = f"{now.day} {now.strftime('%B %Y')}"

    sections = [
        metadata_block if metadata_block else "",
        f"**Generated:** {generated_at}",
        "",
        "\n".join([
            '<div style="background-color: #fffde7; padding: 16px; border-radius: 8px; border: 1px solid #fff176; margin: 16px 0;">',
            "",
            "## For Analyst Review",
            "",
            "### High-level summary bullets",
            state["summary_bullets"],
            "",
            "### Unobvious points",
            state["unobvious_points"],
            "",
            "### The Spark",
            state["spark"],
            "</div>",
        ]),
        "",
        "---",
        "",
        "# Morning Note",
        note_date,
        "",
        f"## {state.get('company', '')}",
        "\n".join([
            '<div style="background-color: #e8f5e9; padding: 16px; border-radius: 8px; border: 1px solid #a5d6a7; margin: 16px 0;">',
            "",
            f"### {state['title']}",
            "",
            state["top_bullets"],
            "",
            state["executive_summary"],
            "</div>",
        ]),
        "",
        "### The Financials",
        state["financials"],
        "",
        "### The Commercial",
        state["commercial"],
        "",
        "### The Segments",
        state["segments"],
        "",
        "### The Outlook",
        state["outlook"],
    ]
    return "\n".join(part for part in sections if part is not None).strip() + "\n"


def render_document_sections_markdown(state: ResearchState) -> str | None:
    sections = state.get("document_sections")
    if not sections:
        return None
    header = _build_header(state)
    section_order = [
        "KEY_HIGHLIGHTS",
        "FINANCIAL_RESULTS",
        "COMMERCIAL_UPDATE",
        "SEGMENT_PERFORMANCE",
        "OUTLOOK_GUIDANCE",
    ]
    parts = [header, "# Document sections"]
    for key in section_order:
        if key in sections and sections[key].strip():
            title = key.replace("_", " ").title()
            parts.append(f"## {title}\n\n{sections[key].strip()}")
    for key in sorted(sections):
        if key not in section_order and sections[key].strip():
            title = key.replace("_", " ").title()
            parts.append(f"## {title}\n\n{sections[key].strip()}")
    return "\n\n".join(parts).strip() + "\n"


def build_payload(state: ResearchState) -> dict[str, Any]:
    return {
        "title": state["title"],
        "company": state.get("company"),
        "ticker": state.get("ticker"),
        "analyst": state.get("analyst"),
        "llm_model": state.get("llm_model"),
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
