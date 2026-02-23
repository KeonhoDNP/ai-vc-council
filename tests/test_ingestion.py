import pytest

from council.ingestion import IngestionError, build_startup_context


def test_build_startup_context_combines_sections() -> None:
    context = build_startup_context(
        deck_text="Deck content",
        webpage_text="Web content",
        additional_notes="Extra notes",
    )
    assert "## Deck Text" in context
    assert "## Webpage Text" in context
    assert "## Additional Notes" in context


def test_build_startup_context_requires_input() -> None:
    with pytest.raises(IngestionError):
        build_startup_context()
