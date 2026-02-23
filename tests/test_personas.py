from council.personas import PERSONAS


def test_persona_count_is_16() -> None:
    assert len(PERSONAS) == 16


def test_requested_members_present() -> None:
    names = {persona.name for persona in PERSONAS}
    assert "Masayoshi Son" in names
    assert "Peter Thiel" in names
    assert "Vinod Khosla" in names
