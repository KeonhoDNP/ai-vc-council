"""Input ingestion utilities for deck files and startup webpages."""

from __future__ import annotations

import io
import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

try:  # Optional fallback extractor for some CJK-encoded PDFs.
    import fitz  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    fitz = None


DEFAULT_MAX_SOURCE_CHARS = 120_000
DEFAULT_TIMEOUT_SECONDS = 20


class IngestionError(RuntimeError):
    """Raised when user-provided source content cannot be extracted."""


@dataclass(frozen=True)
class IngestedSource:
    source_type: str
    content: str


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def _clip_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    clipped = text[:max_chars]
    return f"{clipped}\n\n[TRUNCATED: input exceeded {max_chars} characters]"


def _text_quality_score(text: str) -> int:
    if not text.strip():
        return 0

    hangul_chars = len(re.findall(r"[가-힣]", text))
    alnum_chars = sum(1 for ch in text if ch.isalnum())
    replacement_chars = text.count("\ufffd")
    suspicious_boxes = text.count("□")
    return (2 * hangul_chars) + alnum_chars - (5 * replacement_chars) - (2 * suspicious_boxes)


def _extract_with_pypdf(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    chunks: list[str] = []

    for page_num, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        clean_text = _normalize_whitespace(raw_text)
        if clean_text:
            chunks.append(f"[Page {page_num}] {clean_text}")

    return "\n\n".join(chunks)


def _extract_with_pymupdf(pdf_bytes: bytes) -> str:
    if fitz is None:
        return ""

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    chunks: list[str] = []
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        raw_text = page.get_text("text") or ""
        clean_text = _normalize_whitespace(raw_text)
        if clean_text:
            chunks.append(f"[Page {page_num + 1}] {clean_text}")

    return "\n\n".join(chunks)


def extract_text_from_pdf_bytes(
    pdf_bytes: bytes, *, max_chars: int = DEFAULT_MAX_SOURCE_CHARS
) -> str:
    """Extract readable text from a PDF file uploaded by the user."""
    candidates: list[str] = []

    try:
        candidates.append(_extract_with_pypdf(pdf_bytes))
    except Exception:
        candidates.append("")

    try:
        candidates.append(_extract_with_pymupdf(pdf_bytes))
    except Exception:
        candidates.append("")

    best_text = max(candidates, key=_text_quality_score, default="")
    best_score = _text_quality_score(best_text)

    if not best_text.strip():
        raise IngestionError(
            "No extractable text found in the PDF. If this Korean deck is image-only or "
            "font-embedded, run OCR first, then upload again."
        )

    if best_score < 80:
        # This usually means garbled extraction from scanned/image-heavy decks.
        best_text = (
            "[EXTRACTION WARNING] Text quality is low. For Korean scanned PDFs, OCR "
            "conversion is recommended before analysis.\n\n"
            f"{best_text}"
        )

    return _clip_text(best_text, max_chars)


def _validate_public_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise IngestionError("URL must start with http:// or https://")
    if not parsed.netloc:
        raise IngestionError("URL is missing a hostname")

    hostname = parsed.hostname or ""
    if hostname in {"localhost", "127.0.0.1", "::1"}:
        raise IngestionError("Localhost URLs are not allowed")

    # Reject private IP literals to reduce SSRF risk in self-hosted deployments.
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            raise IngestionError("Private or loopback IP URLs are not allowed")
    except ValueError:
        pass

    return parsed.geturl()


def extract_text_from_url(
    url: str,
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_chars: int = DEFAULT_MAX_SOURCE_CHARS,
) -> str:
    """Fetch and extract text from a public startup webpage."""
    clean_url = _validate_public_url(url)

    try:
        response = requests.get(
            clean_url,
            timeout=timeout_seconds,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; VC-Council-Agent/1.0; +https://localhost)"
                )
            },
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise IngestionError(f"Failed to fetch URL: {exc}") from exc

    soup = BeautifulSoup(response.text, "html.parser")

    for tag_name in ["script", "style", "noscript", "svg", "iframe"]:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    chunks: list[str] = []

    if soup.title and soup.title.string:
        chunks.append(f"Title: {_normalize_whitespace(soup.title.string)}")

    meta_description = soup.find("meta", attrs={"name": "description"})
    if meta_description and meta_description.get("content"):
        chunks.append(
            f"Meta Description: {_normalize_whitespace(meta_description['content'])}"
        )

    for heading in soup.find_all(["h1", "h2", "h3"]):
        text = _normalize_whitespace(heading.get_text(" ", strip=True))
        if text:
            chunks.append(f"Heading: {text}")

    for paragraph in soup.find_all(["p", "li"]):
        text = _normalize_whitespace(paragraph.get_text(" ", strip=True))
        if len(text) >= 40:
            chunks.append(text)

    if not chunks:
        raise IngestionError("Could not extract readable text from the webpage")

    deduped: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        if chunk not in seen:
            seen.add(chunk)
            deduped.append(chunk)

    return _clip_text("\n".join(deduped), max_chars)


def build_startup_context(
    *,
    deck_text: str | None = None,
    webpage_text: str | None = None,
    additional_notes: str | None = None,
    max_chars: int = 140_000,
) -> str:
    """Combine all available startup input into one council-ready context block."""
    sections: list[str] = []

    if deck_text:
        sections.append(f"## Deck Text\n{deck_text.strip()}")

    if webpage_text:
        sections.append(f"## Webpage Text\n{webpage_text.strip()}")

    if additional_notes and additional_notes.strip():
        sections.append(f"## Additional Notes\n{additional_notes.strip()}")

    if not sections:
        raise IngestionError("No startup input provided")

    combined = "\n\n".join(sections)
    return _clip_text(combined, max_chars)
