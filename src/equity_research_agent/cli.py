from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pdfplumber

from rich.console import Console
from rich.panel import Panel

from .config import Settings
from .llm import ResearchClient
from .storage import ArtifactStore
from .workflow import build_workflow

console = Console()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an equity research draft from pasted text using Claude + LangGraph."
    )
    parser.add_argument("--text", help="Raw input text to analyse.")
    parser.add_argument("--input-file", type=Path, help="Path to a text file containing the source text.")
    parser.add_argument("--company", help="Optional company name metadata.")
    parser.add_argument("--ticker", help="Optional ticker metadata.")
    parser.add_argument("--analyst", help="Optional requesting analyst or desk metadata.")
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload output artifacts to Azure Blob Storage after local generation.",
    )
    return parser.parse_args()


def _extract_pdf_text(path: Path) -> str:
    with pdfplumber.open(path) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return "\n\n".join(pages).strip()


def _load_input_text(args: argparse.Namespace) -> str:
    file_text = ""
    if args.input_file:
        if args.input_file.suffix.lower() == ".pdf":
            file_text = _extract_pdf_text(args.input_file)
        else:
            file_text = args.input_file.read_text(encoding="utf-8").strip()

    typed_text = args.text.strip() if args.text else ""

    if typed_text and file_text:
        return f"[User note]\n{typed_text}\n\n[Document: {args.input_file.name}]\n{file_text}"
    if file_text:
        return file_text
    if typed_text:
        return typed_text
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    raise ValueError("Provide --text, --input-file, or pipe text via stdin.")


def main() -> None:
    args = _parse_args()
    raw_input = _load_input_text(args)
    if not raw_input:
        raise ValueError("Input text is empty.")

    settings = Settings()
    client = ResearchClient(settings)
    workflow = build_workflow(client)

    initial_state = {
        "raw_input": raw_input,
        "company": args.company,
        "ticker": args.ticker,
        "analyst": args.analyst,
        "llm_model": f"{settings.llm_provider}/{settings.llm_model}",
    }

    console.print("[bold cyan]Running equity research workflow...[/bold cyan]")
    t0 = time.perf_counter()
    try:
        state = workflow.invoke(initial_state)

        store = ArtifactStore(settings)
        persisted = store.save_local(
            title=state["title"],
            analyst_markdown=state["final_analyst_markdown"],
            morning_note_markdown=state["final_morning_note_markdown"],
            payload=state["final_payload"],
        )

        console.print(Panel.fit(state["final_markdown"], title="Generated research note"))
        console.print(f"\nSaved analyst review: [green]{persisted.analyst_markdown_path}[/green]")
        console.print(f"Saved morning note:   [green]{persisted.morning_note_markdown_path}[/green]")
        console.print(f"Saved JSON:           [green]{persisted.json_path}[/green]")

        should_upload = args.upload or settings.upload_to_azure
        if should_upload:
            urls = store.upload(persisted)
            console.print("\n[bold green]Uploaded to Azure Blob Storage:[/bold green]")
            for label, url in urls.items():
                console.print(f"- {label}: {url}")
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        console.print(f"\n[bold red]Workflow failed after {elapsed:.1f}s[/bold red]: {exc}")
        raise

    elapsed = time.perf_counter() - t0
    console.print(f"\n[bold green]Completed in {elapsed:.1f}s[/bold green]")


if __name__ == "__main__":
    main()
