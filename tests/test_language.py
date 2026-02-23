from council.language import detect_primary_language, resolve_output_language


def test_detect_primary_language_korean() -> None:
    text = """
    이 회사는 AI 기반 물류 최적화 솔루션을 제공합니다.
    고객사는 이커머스 기업이며 월 반복 매출이 빠르게 증가하고 있습니다.
    """
    assert detect_primary_language(text) == "ko"


def test_detect_primary_language_english() -> None:
    text = "This startup builds AI software for supply chain planning and pricing."
    assert detect_primary_language(text) == "en"


def test_resolve_output_language_auto() -> None:
    text = "한국 시장을 중심으로 SaaS를 확장하고 있습니다."
    assert resolve_output_language("auto", text) == "ko"


def test_resolve_output_language_explicit() -> None:
    text = "한국어 텍스트가 있어도 영어로 출력하고 싶다"
    assert resolve_output_language("en", text) == "en"
