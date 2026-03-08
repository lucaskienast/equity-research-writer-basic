PYTHON ?= python3

install:
	$(PYTHON) -m pip install -e ".[dev]"

run-sample:
	$(PYTHON) -m equity_research_agent.cli --input-file examples/sample_input.txt --company "Example Co" --ticker EXM

test:
	pytest

lint:
	ruff check .
