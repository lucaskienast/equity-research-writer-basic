from equity_research_agent.renderer import build_payload, render_markdown


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

    assert "# Margins Hold Despite Softer Demand" in markdown
    assert "## Top bullets" in markdown
    assert "## The Financials" in markdown
    assert "## The Outlook" in markdown


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
