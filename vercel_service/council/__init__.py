"""AI VC Council package."""

from council.engine import CouncilResult, CouncilRunConfig, run_council_analysis
from council.ingestion import IngestionError, build_startup_context, extract_text_from_pdf_bytes, extract_text_from_url
from council.language import detect_primary_language, output_language_label, resolve_output_language
from council.llm_client import LLMClientError, OpenAIChatClient

__all__ = [
    "CouncilResult",
    "CouncilRunConfig",
    "IngestionError",
    "LLMClientError",
    "OpenAIChatClient",
    "build_startup_context",
    "detect_primary_language",
    "extract_text_from_pdf_bytes",
    "extract_text_from_url",
    "output_language_label",
    "resolve_output_language",
    "run_council_analysis",
]
