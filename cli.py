from __future__ import annotations

import argparse
import os
from pathlib import Path

from council import (
    CouncilRunConfig,
    IngestionError,
    LLMClientError,
    OpenAIChatClient,
    build_startup_context,
    extract_text_from_pdf_bytes,
    extract_text_from_url,
    run_council_analysis,
)


def _read_notes(notes_path: str | None) -> str | None:
    if not notes_path:
        return None
    return Path(notes_path).read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AI VC Council from CLI")
    parser.add_argument("--company", help="Startup name", default=None)
    parser.add_argument("--pdf", help="Path to pitch deck PDF", default=None)
    parser.add_argument("--url", help="Startup webpage URL", default=None)
    parser.add_argument("--notes-file", help="Path to extra notes text file", default=None)
    parser.add_argument("--model", help="Model name", default=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
    parser.add_argument("--mode", choices=["fast", "deep"], default="fast")
    parser.add_argument("--language", choices=["auto", "en", "ko"], default="auto")
    parser.add_argument("--temperature", type=float, default=0.3)
    parser.add_argument("--max-tokens", type=int, default=4000)
    parser.add_argument("--out", help="Output markdown path", default="vc_council_report.md")
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set")

    deck_text = None
    if args.pdf:
        deck_text = extract_text_from_pdf_bytes(Path(args.pdf).read_bytes())

    webpage_text = None
    if args.url:
        webpage_text = extract_text_from_url(args.url)

    notes = _read_notes(args.notes_file)

    context = build_startup_context(
        deck_text=deck_text,
        webpage_text=webpage_text,
        additional_notes=notes,
    )

    client = OpenAIChatClient()
    config = CouncilRunConfig(
        model=args.model,
        mode=args.mode,
        output_language=args.language,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )

    def progress(stage: str, message: str) -> None:
        print(f"[{stage}] {message}")

    result = run_council_analysis(
        startup_context=context,
        llm_client=client,
        config=config,
        company_name=args.company,
        progress=progress,
    )

    out_path = Path(args.out)
    out_path.write_text(result.full_markdown, encoding="utf-8")
    print(f"Saved: {out_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (IngestionError, LLMClientError) as exc:
        raise SystemExit(str(exc))
