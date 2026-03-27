from equity_research_agent.renderer import (
    build_payload,
    render_markdown,
    _escape_markdown_chars,
    build_perspective_state,
    render_analyst_markdown,
    render_document_sections_markdown,
    render_morning_note_markdown,
)


def test_render_markdown_contains_core_sections():
    state = {
        "title": "Margins Hold Despite Softer Demand",
        "company": "Example Co",
        "ticker": "EXM",
        "analyst": "Equity Research",
        "summary_bullets": "- Revenue rose.\n- Margins expanded.",
        "unobvious_points": "- Pricing offset softer volumes.",
        "spark": "A concise spark paragraph.",
        "financials": "A financial paragraph.",
        "commercial": "A commercial paragraph.",
        "segments": "A segments paragraph.",
        "outlook": "An outlook paragraph.",
        "top_bullets": "- Financials\n- Commercial\n- Segments\n- Outlook",
        "executive_summary": "A top summary paragraph.",
    }

    markdown = render_markdown(state)

    assert "Margins Hold Despite Softer Demand" in markdown
    assert "## For Analyst Review" in markdown
    assert "### [Financials]" in markdown
    assert "### [Outlook]" in markdown


def test_build_payload_keeps_raw_input():
    state = {
        "title": "Test Title",
        "summary_bullets": "- A",
        "unobvious_points": "- B",
        "spark": "Spark",
        "financials": "Financials",
        "commercial": "Commercial",
        "segments": "Segments",
        "outlook": "Outlook",
        "top_bullets": "- 1\n- 2\n- 3\n- 4",
        "executive_summary": "Summary",
        "raw_input": "source text",
    }

    payload = build_payload(state)
    assert payload["raw_input"] == "source text"
    assert payload["title"] == "Test Title"


def _full_state() -> dict:
    return {
        "title": "Test Title",
        "company": "Example Co",
        "ticker": "EXM",
        "analyst": "J. Smith",
        "summary_bullets": "- Bullet 1",
        "unobvious_points": "- Point 1",
        "spark": "The spark.",
        "financials": "Financials text.",
        "commercial": "Commercial text.",
        "segments": "Segments text.",
        "outlook": "Outlook text.",
        "top_bullets": "- Top 1",
        "executive_summary": "Summary.",
        "raw_input": "raw",
    }


def test_render_analyst_markdown_contains_key_sections():
    state = _full_state()
    md = render_analyst_markdown(state)
    assert "For Analyst Review" in md
    assert "High-level summary bullets" in md
    assert "Unobvious points" in md
    assert "The Spark" in md


def test_render_morning_note_contains_key_sections():
    state = _full_state()
    md = render_morning_note_markdown(state)
    assert "Morning Note" in md
    assert "Test Title" in md
    assert "Top 1" in md


def test_render_document_sections_none_when_absent():
    state = _full_state()
    result = render_document_sections_markdown(state)
    assert result is None


def test_render_document_sections_with_data():
    state = _full_state()
    state["document_sections"] = {"KEY_HIGHLIGHTS": "Revenue up.", "FINANCIAL_RESULTS": "£20m."}
    result = render_document_sections_markdown(state)
    assert result is not None
    assert "Key Highlights" in result
    assert "Revenue up." in result


def test_build_perspective_state_merges():
    state = _full_state()
    overlay = {"summary_bullets": "Optimist bullets"}
    merged = build_perspective_state(state, overlay)
    assert merged["summary_bullets"] == "Optimist bullets"
    assert merged["company"] == "Example Co"


def test_escape_markdown_chars():
    assert _escape_markdown_chars("Price $100 ~est") == r"Price \$100 \~est"
