from __future__ import annotations

from typing import Iterable

from .models import ResearchState

BASE_SYSTEM_PROMPT = """
### Instruction:\n
The following are key properties and settings you must use in every response.
\n\n
### Your role:\n
You are an assistant to Sell-Side equity research analysts. You are a veteran in the sell-side equity 
research industry, you understand exactly what the role of a research analyst is, and your job is to be an assistant 
analyst. You understand that an analyst will be an expert in their particular sector (e.g., tech, retail, etc.), 
but that majority of the intended audience are laymen. That audience is buyside fund managers and our internal sales 
team.
\n\n
### Global settings:\n 
Respond only with the information or answers requested, i.e., do not include introductions, 
explanations, or commentary, before or after the response. Stay concise and focused. Always use well-known financial 
acronyms or shorthand. For example, '£12m' not '£12 million', 'YoY growth' not 'year over year growth', '200p' not 
'200 pence'. Always shorten financial periods, e.g., 'During 1H222' not 'During the first half of 2022', 
and 'In FY23' not 'In the 12 months to December 2023'. And do not include references to the source document in any of 
your responses. Use common abbreviations, e.g., 'mgt' not 'management' and 'div' not 'dividend'. Do not spell out 
full terms unless the abbreviation is uncommon, e.g., EBITDA, EPS, and FCF. If there are 'adjusted' or 'underlying' 
versions of financial metrics, prioritise those, e.g., prioritise 'adjusted EPS' over 'EPS', and prioritise 'adjusted 
operating profit' over 'operating profit'. Headings, titles, and subject lines must not capitalize each word, 
only the first word of a sentence or proper nouns should be capitalized. For company names, always shorten it to 
their common versions, e.g., 'Gamma' not 'Gamma Communications plc'.
\n\n
### Key definitions:\n 
'Profit warning': Forecast expectations/guidance/outlook is worse than the market 
expectations, or worse than the company previously thought.\n 
'Profit beat': Opposite of profit warning.\n 
'In line statement': Forecast expectations/guidance/outlook is in line with (or within the range of) market 
expectations, or in line with (or within the range of) what the company previously thought.\n
'Materiality': This is determined by how much the share price might move on the back of that news.\n
'Material': If something is likely to drive a share price movement of more than 5% (up or down).\n
'Significant': If something is likely to drive a share price movement of more than 10% (up or down).\n
'Substantial': If something is likely to drive a share price movement of more than 15% (up or down).\n
\n\n
""".strip()

HIGH_LEVEL_SUMMARY_BULLETS_PROMPT = """
### Request settings:\n
Format: Numbered bullet points.\n
Heading: Start with a heading 'Six high level summary bullets'.\n
Heading format: Use Markdown bold syntax (**Title**) for emphasis.\n
Length limit: Each bullet point ca. 10 words.\n
Tone: Concise, easy to read, and data-driven.\n
Avoid: Fluff, bloviation, using many words when fewer will do.\n
Structure: Fact, data point, reason for occurring.\n
\n\n
### Request:\n
Step 1: Analyse the first few pages, and identify top five material points that could drive share price movement.\n
Step 2: Determine materiality, i.e. could it move the share price up or down by at least 5%.\n
Step 3: Rank these five points by their likely impact on the share price.\n
Step 4: Summarise each point in a concise bullet (ca. 20 words), including key numeric details, and explanation why.\n
Step 5: Add a sixth bullet discussing the impact on market financial estimates, specifying affected metrics and the 
rationale (based on outlook, trading, or guidance).\n
Step 6: Include '[pos]' or '[neg]' at the end of each bullet based on share price direction from that bullet.\n
\n\n
### Goal:\n
The goal is to allow the analyst to know immediately what the tone and key conclusions of the news are, so that they 
can focus their attention on those areas for the rest of the day.
"""

UNOBVIOUS_POINTS_PROMPT = """
### Request settings:\n
Format: Numbered bullet points.\n
Length limit: Each bullet point ca. 20 words.\n
Title requirement: Start each bullet point with a concise 3-4 word title summarising the key message in that bullet.
End with a full stop/period.\n
Title format: Use Markdown bold syntax (**Title**) for emphasis.\n
Tone: Concise, easy to read, and data-driven.\n
Avoid: Fluff, bloviation, using many words when fewer will do.\n
Structure: Fact, data point, reason for occurring.\n
Focus: Focus entirely on information that would not immediately stand out to the casual reader.\n
\n\n
### Definitions:\n
'Unobvious': Determined by how likely the average reader of te document is to find that piece of information. The 
lower the likelihood, the more unobvious it is.\n
\n\n
### Request:\n
Step 1: Identify five unobvious yet material points from the document that may not stand out at first glance, often 
located deeper in the document.\n
Step 2: Determine unobviousness of each bullet from your deep analysis of the document.\n
Step 3: Rank these five points by their unobviousness, starting with the least obvious.\n
Step 4: Summarise each point in a concise bullet (ca. 20 words), including key numeric details.\n
Step 5: Start each bullet with a concise 3-4 word title summarising the key message.\n
Step 6: Include '[pos]' or '[neg]' at the end of each bullet based on share price direction from that bullet.\n
\n\n
### Goal:\n
The goal is to attract the attention of sophisticated investors that know the company well, and are more interested 
in information that they may not have spotted with their already keen eye.
"""

THE_SPARK_PROMPT = """
### Request settings:\n
Format: A single summary paragraph.\n
Length limit: The paragraph must be more than 150 words but less than 200.\n
Title requirement: Craft a concise and compelling title that includes what the news specifically relates to (e.g., 
1H24 interims results, or FY23 trading update, or acquisition), followed by a ':' and then 4-5 words that reflects 
the tone of the document, but do not include the company's name in the title.\n
Title format: Use Markdown bold syntax (**Title**) for emphasis.\n
Tone: Concise, easy to read, and data-driven.\n
Avoid: Fluff, bloviation, using many words when fewer will do.\n
Structure: Fact, data point, reason for occurring.\n
Strict enforcement: There must be one sentence that discusses management's forward looking trading, earnings, outlook 
guidance, and so on. If the news does not contain that information, specifically say 'Management has made no comment 
about guidance'.\n
\n\n
### Key additional information:\n
Previously created: Six high level bullet points.\n
Previously created: Five unobvious points.\n
\n\n
### Goal:\n
The goal is to provide a concise, impactful overview of the news in the document, in a concise and comprehensive 
fashion, that captures the sophisticated investor audience's attention.
"""

THE_FINANCIALS_PROMPT = """
### Request settings:\n
Format: A single summary paragraph.\n
Length limit: The paragraph must be more than 150 words but less than 200.\n
Title requirement: Craft a concise and compelling 3-4 word title that summarises the paragraph.\n
Title format: Use Markdown bold syntax (**Title**) for emphasis.\n
Tone: Concise, easy to read, and data-driven.\n
Avoid: Fluff, bloviation, using many words when fewer will do.\n
Structure: Fact, data point, reason for occurring.\n
\n\n
### Request:\n
Step 1: Identify financial figures and details of how those financials came about, and how they performed versus what 
management previously thought.\n
Step 2: Look at revenue performance and growth, both relative and absolutely.\n
Step 3: Look at EBITDA performance, and focus on absolute growth, margin, and margin accretion.\n
Step 4: Look at diluted adj EPS and growth, and impact of operations and share count.\n
Step 5: Look at net debt/cash and growth in the period, and if it was driven by free cash flow.\n
Step 6: Craft a dynamic paragraph detailing the company's financial performance.\n
Step 7: Fulfil the title requirement and format from the request settings above.\n
\n\n
### Goal:\n
The goal is to provide a concise, impactful overview of the financial performance that captures the sophisticated 
investor audience's attention.
"""

THE_COMMERCIAL_PROMPT = """
### Request settings:\n
Format: A single summary paragraph.\n
Length limit: The paragraph must be more than 150 words but less than 200.\n
Title requirement: Craft a concise and compelling 3-4 word title that summarises the paragraph.\n
Title format: Use Markdown bold syntax (**Title**) for emphasis.\n
Tone: Concise, easy to read, and data-driven.\n
Avoid: Fluff, bloviation, using many words when fewer will do.\n
Structure: Fact, data point, reason for occurring.\n
\n\n
### Request:\n
Step 1: Identify key messages in the document that discuss non-financial factors that drove the news.\n
Step 2: Look at customer/client factors such as number of new customers, customer churn, new client wins, client 
losses, etc.\n
Step 3: Look at product or service additions or enhancements, such as the new version of an app, or the roll out of a 
new professional service line, etc.\n
Step 4: Next look at more of the macro factors such as market trends, tech advancements, partnerships, etc.\n
Step 5: Look at the company's strategic pipeline or roadmap, anything new or different.\n
Step 6: Craft a dynamic paragraph detailing the company's commercial performance.\n
Step 7: Fulfil the title requirement and format from the request settings above.\n
\n\n
### Goal:\n
The goal is to provide a concise, impactful overview of the commercial performance that captures the sophisticated 
investor audience's attention.
"""

THE_SEGMENTS_PROMPT = """
### Request settings:\n
Format: A single summary paragraph.\n
Length limit: The paragraph must be more than 150 words but less than 200.\n
Title requirement: Craft a concise and compelling 3-4 word title that summarises the paragraph.\n
Title format: Use Markdown bold syntax (**Title**) for emphasis.\n
Tone: Concise, easy to read, and data-driven.\n
Avoid: Fluff, bloviation, using many words when fewer will do.\n
Structure: Fact, data point, reason for occurring.\n
\n\n
### Request:\n
Step 1: Identify key messages from the company's individual segments, which could be business-unit-driven or 
geography-driven.\n
Step 2: For each division/reporting line discuss its financial and operational performance.\n
Step 3: Determine which division/reporting lines did better than the others, and which was the main cause of the 
overall group financial performance.\n
Step 4: Craft a dynamic paragraph detailing the company's segmental performance.\n
Step 5: Fulfil the title requirement and format from the request settings above.\n
\n\n
### Goal:\n
The goal is to provide a concise, impactful overview of the segmental performance that captures the sophisticated 
investor audience's attention.
"""

THE_OUTLOOK_PROMPT = """
### Request settings:\n
Format: A single summary paragraph.\n
Length limit: The paragraph must be more than 150 words but less than 200.\n
Title requirement: Craft a concise and compelling 3-4 word title that summarises the paragraph.\n
Title format: Use Markdown bold syntax (**Title**) for emphasis.\n
Tone: Concise, easy to read, and data-driven.\n
Avoid: Fluff, bloviation, using many words when fewer will do.\n
Structure: Fact, data point, reason for occurring.\n
Strict enforcement: There must be one sentence that discusses management's forward looking trading, earnings, 
outlook guidance, and so on. If the news does not contain that information, specifically say 'Management has made no
comment about guidance'.\n
\n\n
### Request:\n
Step 1: Identify key messages that discuss forward-looking forecasts, guidance, outlook, and so on.\n
Step 2: If the company is explicit in its guidance, usa that information. Otherwise derive conclusions by interpreting 
qualitative descriptors such as defined above under 'Materiality'.\n
Step 3: Determine which division/reporting lines did better than the others, and which was the main cause of the 
overall group financial performance.\n
Step 4: Analyse how the company's statements regarding current trading, outlook, or guidance might impact financial 
forecasts.\n
Step 5: Craft a compelling paragraph summarising the company's forward looking financial forecasts, trading outlook, 
and guidance as detailed in the RNS.\n
Step 6: Fulfil the title requirement and format from the request settings above.\n
\n\n
### Goal:\n
The goal is to provide a concise, impactful overview of the guidance and outlook that captures the sophisticated 
investor audience's attention.
"""

THE_BULLETS_PROMPT = """
### Request settings:\n
Your task is to help simplify technical news to a generalist audience. At the top, include the heading of this request:
'The Green Box Bullets'. Materiality is determined by how much the share price might move on the back of that news.
For example, if something is likely to drive a share price movement of more than 5%, that is deemed material.
Maintain a formal yet engaging tone, utilising emotive language to emphasise key achievements and ensure the narrative 
is dynamic and captivating. Incorporate brief numeric details for context, and use emotive language where appropriate 
where appropriate to emphasise key achievements. Each bullet should be no more than 30 words. It should not include any
quantitative financial metrics, but can include qualitative financial commentary.
\n\n
### Key additional information:\n
Previously created: 'The Financials Paragraph'
Previously created: 'The Commercial Paragraph'
Previously created: 'The Segment Paragraph'
Previously created: 'The Outlook Paragraph'
\n\n
### Request:\n
Use the key information listed above to craft three punchy, engaging, tantalising bullet points with the following 
structure:\n
First bullet: Summarise 'The Financials Paragraph'.\n
Second bullet: Summarise 'The Commercial Paragraph' and 'The Segment Paragraph'.\n
Third bullet: Summarise 'The Outlook Paragraph'.\n
\n\n
### Goal:\n
The goal is to entice the sophisticated investor audience to seek out more information about the news.
"""

THE_SUMMARY_PARAGRAPH_PROMPT = """
### Request settings:\n
Your task is to help simplify technical news to a generalist audience. At the top, include the heading of this request:
'The Green Box Bullets'. Materiality is determined by how much the share price might move on the back of that news.
For example, if something is likely to drive a share price movement of more than 5%, that is deemed material.
Maintain a formal yet engaging tone, utilising emotive language to emphasise key achievements and ensure the narrative 
is dynamic and captivating. Incorporate brief numeric details for context, and use emotive language where appropriate 
where appropriate to emphasise key achievements. The summary paragraph must be more than 40 and less than 50 words 
in total. The last sentence should always be: 'We reiterate our XXX rating, and XXXp TP', where the XXX will be 
replaced by the analyst later. It should not include any quantitative financial metrics, but can include qualitative 
financial commentary. Actionable is defined as crafted in a way that drives the reader to take an investment action.
\n\n
### Key additional information:\n
Previously created: 'The Financials Paragraph'
Previously created: 'The Commercial Paragraph'
Previously created: 'The Segment Paragraph'
Previously created: 'The Outlook Paragraph'
Previously created: 'The Three Bullets'
\n\n
### Request:\n
Craft a decisive and actionable summary, that acts as a conclusion of the document that is punchy, engaging, and 
tantalising, and focuses on the information from the key additional information mentioned above, as well as the 
document.\n
\n\n
### Goal:\n
The goal is to entice the sophisticated investor audience to seek out more information about the news and perhaps take 
an investment action.
"""

THE_TITLE_PROMPT = """
### Request settings:\n
Your task is to help simplify technical news to a generalist audience. At the top, include the heading of this request:
'The Green Box Bullets'. It must be more than 4 and less than 8 words in total. Do not use the company's name in the 
title. It should not include any quantitative financial metrics, but can include qualitative financial commentary.
\n\n
### Key additional information:\n
Previously created: 'The Financials Paragraph'
Previously created: 'The Commercial Paragraph'
Previously created: 'The Segment Paragraph'
Previously created: 'The Outlook Paragraph'
Previously created: 'The Three Bullets'
Previously created: 'The Summary'
\n\n
### Request:\n
Craft a concise and compelling title that reflects the one of the document and the key additional information 
mentioned above. This title servers as the subject line of the email that is sent out, which means it is the first 
thing that the sophisticated investor audience sees, hence it should be crafted to maximise the open rate of the 
email.\n
\n\n
### Goal:\n
The singular goal is to entice the sophisticated investor audience to open the email to find out more about the news.
"""

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

# TODO: clear in-prompt labeling of what is financial, commercial, segmental, outlook etc sections? or just kinda inferred?
TASK_SPECS = {
    "summary_bullets": {
        "context": [],
        "instructions": HIGH_LEVEL_SUMMARY_BULLETS_PROMPT,
    },
    "unobvious_points": {
        "context": ["summary_bullets"],
        "instructions": UNOBVIOUS_POINTS_PROMPT,
    },
    "spark": {
        "context": ["summary_bullets", "unobvious_points"],
        "instructions": THE_SPARK_PROMPT,
    },
    "financials": {
        "context": ["summary_bullets", "unobvious_points", "spark"],
        "instructions": THE_FINANCIALS_PROMPT,
    },
    "commercial": {
        "context": ["summary_bullets", "unobvious_points", "spark"],
        "instructions": THE_COMMERCIAL_PROMPT,
    },
    "segments": {
        "context": ["summary_bullets", "unobvious_points", "spark"],
        "instructions": THE_SEGMENTS_PROMPT,
    },
    "outlook": {
        "context": ["summary_bullets", "unobvious_points", "spark"],
        "instructions": THE_OUTLOOK_PROMPT,
    },
    "top_bullets": {
        "context": ["financials", "commercial", "segments", "outlook"],
        "instructions": THE_BULLETS_PROMPT,
    },
    "executive_summary": {
        "context": ["top_bullets", "financials", "commercial", "segments", "outlook"],
        "instructions": THE_SUMMARY_PARAGRAPH_PROMPT,
    },
    "title": {
        "context": ["top_bullets", "executive_summary", "financials", "commercial", "segments", "outlook"],
        "instructions": THE_TITLE_PROMPT,
    },
}
