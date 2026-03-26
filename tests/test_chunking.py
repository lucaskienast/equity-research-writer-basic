from equity_research_agent.prompts import build_task_prompt, TASK_SPECS
from equity_research_agent.workflow import _parse_document_sections

SAMPLE_SECTIONS_OUTPUT = """
[SECTION: KEY_HIGHLIGHTS]
Revenue up 10% YoY. CEO said results ahead of expectations.

[SECTION: FINANCIAL_RESULTS]
Revenue £100m, EBITDA £20m, margin 20%, EPS 10p, net debt £50m.

[SECTION: COMMERCIAL_UPDATE]
New contract wins in UK. Churn reduced by 2pp. New product launched.

[SECTION: SEGMENT_PERFORMANCE]
UK division up 15%, Europe flat, APAC declined 5%.

[SECTION: OUTLOOK_GUIDANCE]
FY25 revenue guidance £110m–£115m. Management confident in H2 outlook.
""".strip()


def test_parse_document_sections_happy_path():
    sections = _parse_document_sections(SAMPLE_SECTIONS_OUTPUT)
    assert set(sections.keys()) == {
        "KEY_HIGHLIGHTS",
        "FINANCIAL_RESULTS",
        "COMMERCIAL_UPDATE",
        "SEGMENT_PERFORMANCE",
        "OUTLOOK_GUIDANCE",
    }
    assert "Revenue up 10%" in sections["KEY_HIGHLIGHTS"]
    assert "EBITDA £20m" in sections["FINANCIAL_RESULTS"]
    assert "FY25 revenue guidance" in sections["OUTLOOK_GUIDANCE"]


def test_parse_document_sections_partial():
    partial_output = """
[SECTION: KEY_HIGHLIGHTS]
Headline numbers strong.

[SECTION: FINANCIAL_RESULTS]
Revenue £50m, margin 15%.

[SECTION: OUTLOOK_GUIDANCE]
FY guidance maintained.
""".strip()
    sections = _parse_document_sections(partial_output)
    assert len(sections) == 3
    assert "KEY_HIGHLIGHTS" in sections
    assert "FINANCIAL_RESULTS" in sections
    assert "OUTLOOK_GUIDANCE" in sections


def test_parse_document_sections_empty():
    sections = _parse_document_sections("This is not a valid section output at all.")
    assert sections == {}


def _make_state(document_sections=None):
    return {
        "raw_input": "Full raw document text with lots of detail.",
        "company": "Example Co",
        "ticker": "EXM",
        "analyst": "J. Smith",
        "document_sections": document_sections,
    }


def _build(task_name, state):
    spec = TASK_SPECS[task_name]
    return build_task_prompt(task_name, spec["instructions"], state, spec["context"])


def test_build_task_prompt_uses_sections():
    sections = _parse_document_sections(SAMPLE_SECTIONS_OUTPUT)
    state = _make_state(document_sections=sections)
    prompt = _build("financials", state)

    assert "EBITDA £20m" in prompt  # FINANCIAL_RESULTS present
    assert "New contract wins" not in prompt  # COMMERCIAL_UPDATE absent
    assert "UK division" not in prompt  # SEGMENT_PERFORMANCE absent
    assert "FY25 revenue" not in prompt  # OUTLOOK_GUIDANCE absent


def test_build_task_prompt_fallback():
    state = _make_state(document_sections=None)
    prompt = _build("financials", state)

    assert "Full raw document text" in prompt


def test_build_task_prompt_no_doc_for_late_tasks():
    sections = _parse_document_sections(SAMPLE_SECTIONS_OUTPUT)
    state = {
        **_make_state(document_sections=sections),
        "financials": "Financials paragraph.",
        "commercial": "Commercial paragraph.",
        "segments": "Segments paragraph.",
        "outlook": "Outlook paragraph.",
    }
    prompt = _build("top_bullets", state)

    assert "Source text:" not in prompt
    assert "Revenue up 10%" not in prompt  # no raw doc section
    assert "Financials paragraph." in prompt  # prior context present


def test_build_task_prompt_summary_bullets_all_sections():
    sections = _parse_document_sections(SAMPLE_SECTIONS_OUTPUT)
    state = _make_state(document_sections=sections)
    prompt = _build("summary_bullets", state)

    assert "KEY_HIGHLIGHTS" in prompt
    assert "FINANCIAL_RESULTS" in prompt
    assert "COMMERCIAL_UPDATE" in prompt
    assert "SEGMENT_PERFORMANCE" in prompt
    assert "OUTLOOK_GUIDANCE" in prompt
