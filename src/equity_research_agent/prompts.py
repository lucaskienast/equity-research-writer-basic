from __future__ import annotations

from typing import Iterable

from .models import ResearchState

BASE_SYSTEM_PROMPT = """
You are an AI writing assistant supporting the sell-side equity research department of a global
investment bank.

Your audience is sophisticated institutional investors and internal equity research analysts.
Write with precision, compression, and analytical judgement.

Style guide:
- Use institutional market language naturally: YoY, QoQ, H1, H2, FY, margin, beat, miss,
  guidance, consensus, run-rate, mix, pricing, volumes, EBIT, EBITDA, EPS, FCF.
- Prefer crisp, high-signal sentences over marketing language.
- Do not invent data. If a figure is missing, say it is undisclosed or not provided.
- Highlight what changed, why it matters, and whether it is likely material.
- Be comfortable flagging weak quality of earnings, soft demand, channel pressure,
  mix deterioration, or guidance risk where supported by the input.
- Materiality means a factor likely to alter a sophisticated investor's view of earnings,
  cash flow, valuation, capital allocation, or the stock narrative.
- Profit warning means management is signalling downside versus prior guidance,
  consensus expectations, or the market's prior understanding.
- If the source is ambiguous, say so explicitly rather than overstating certainty.
- Avoid emojis, hype, exclamation marks, and generic boilerplate.
""".strip()


def _metadata_lines(state: ResearchState) -> str:
    lines = []
    if state.get("company"):
        lines.append(f"Company: {state['company']}")
    if state.get("ticker"):
        lines.append(f"Ticker: {state['ticker']}")
    if state.get("analyst"):
        lines.append(f"Analyst: {state['analyst']}")
    return "\n".join(lines)


def _existing_context(state: ResearchState, keys: Iterable[str]) -> str:
    chunks: list[str] = []
    for key in keys:
        value = state.get(key)
        if value:
            pretty_name = key.replace("_", " ").title()
            chunks.append(f"[{pretty_name}]\n{value}")
    return "\n\n".join(chunks)


def build_task_prompt(task_name: str, instructions: str, state: ResearchState, context_keys: Iterable[str]) -> str:
    metadata = _metadata_lines(state)
    context = _existing_context(state, context_keys)

    pieces = [
        f"Task: {task_name}",
        instructions.strip(),
    ]
    if metadata:
        pieces.append("Metadata:\n" + metadata)
    pieces.append("Source text:\n" + state["raw_input"].strip())
    if context:
        pieces.append("Previously generated context:\n" + context)
    return "\n\n".join(pieces)


TASK_SPECS = {
    "summary_bullets": {
        "context": [],
        "instructions": """
Produce 5-7 high-level summary bullets.
Formatting rules:
- Output bullets only.
- Each bullet must start with '- '.
- Each bullet must be one sentence.
- Focus on the most decision-useful facts and shifts.
- Keep the full section under 120 words.
Tone: concise, factual, investor-facing.
""",
    },
    "unobvious_points": {
        "context": ["summary_bullets"],
        "instructions": """
Extract 3-5 unobvious points that a sophisticated investor might miss on a first read.
Formatting rules:
- Output bullets only.
- Each bullet must start with '- '.
- Each bullet must explain why the point matters.
- Avoid repeating the obvious headline facts unless you add new analytical value.
- Keep the full section under 140 words.
Tone: analytical, sceptical, high-signal.
""",
    },
    "spark": {
        "context": ["summary_bullets", "unobvious_points"],
        "instructions": """
Write 'The Spark' as one concise paragraph.
Formatting rules:
- Output a single paragraph only.
- 55-90 words.
- Capture the core investment relevance of the news and why the buy-side should care now.
- Sound sharp and differentiated, not generic.
""",
    },
    "financials": {
        "context": ["summary_bullets", "unobvious_points", "spark"],
        "instructions": """
Write 'The Financials' as one concise paragraph.
Formatting rules:
- Output a single paragraph only.
- 70-120 words.
- Focus on revenue, profit, margins, cash, leverage, balance sheet, costs, or earnings quality where relevant.
- Emphasise delta versus prior expectations, prior periods, or market assumptions if evident.
""",
    },
    "commercial": {
        "context": ["summary_bullets", "unobvious_points", "spark"],
        "instructions": """
Write 'The Commercial' as one concise paragraph.
Formatting rules:
- Output a single paragraph only.
- 70-120 words.
- Focus on demand, orders, pricing, volumes, customer behaviour, competitive positioning,
  channel dynamics, backlog, mix, or market-share implications.
""",
    },
    "segments": {
        "context": ["summary_bullets", "unobvious_points", "spark"],
        "instructions": """
Write 'The Segments' as one concise paragraph.
Formatting rules:
- Output a single paragraph only.
- 70-120 words.
- Focus on division, geography, product-line, or channel performance where disclosed.
- If segment disclosure is thin, explicitly say segment detail is limited and infer cautiously.
""",
    },
    "outlook": {
        "context": ["summary_bullets", "unobvious_points", "spark"],
        "instructions": """
Write 'The Outlook' as one concise paragraph.
Formatting rules:
- Output a single paragraph only.
- 70-120 words.
- Focus on guidance, management tone, risks, catalysts, visibility, consensus implications,
  and whether the read-across is positive, negative, or mixed.
""",
    },
    "top_bullets": {
        "context": ["financials", "commercial", "segments", "outlook"],
        "instructions": """
Draft exactly 4 punchy top-of-document bullets.
Formatting rules:
- Output exactly 4 bullets only.
- Each bullet must start with '- '.
- Bullet 1 summarises Financials.
- Bullet 2 summarises Commercial.
- Bullet 3 summarises Segments.
- Bullet 4 summarises Outlook.
- Make them engaging and investor-relevant without becoming sensational.
- Each bullet should be 10-20 words.
""",
    },
    "executive_summary": {
        "context": ["top_bullets", "financials", "commercial", "segments", "outlook"],
        "instructions": """
Write the top summary paragraph for the final document.
Formatting rules:
- Output a single paragraph only.
- 80-140 words.
- Synthesize the financials, commercial, segments, and outlook into one decisive takeaway.
- The conclusion should help an analyst or salesperson know what to say to a client immediately.
""",
    },
    "title": {
        "context": ["top_bullets", "executive_summary", "financials", "commercial", "segments", "outlook"],
        "instructions": """
Write the document title.
Formatting rules:
- Output one line only.
- Maximum 12 words.
- Make it concise, compelling, and investment-relevant.
- No quotation marks.
- Avoid generic titles like 'Company update' or 'Mixed results'.
""",
    },
}
