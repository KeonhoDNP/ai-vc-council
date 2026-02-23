"""Persona definitions for the VC council simulation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Persona:
    name: str
    emoji: str
    tagline: str
    philosophy: str


PERSONAS: list[Persona] = [
    Persona(
        name="Peter Thiel",
        emoji="🟣",
        tagline="Zero to One",
        philosophy="Contrarian thesis, monopoly outcomes, and non-consensus secrets.",
    ),
    Persona(
        name="Marc Andreessen",
        emoji="🔵",
        tagline="Software Leverage",
        philosophy="Software-platform expansion that rewrites industry structure.",
    ),
    Persona(
        name="Bill Gurley",
        emoji="🩷",
        tagline="Unit Economics",
        philosophy="LTV/CAC rigor, marketplace dynamics, and valuation discipline.",
    ),
    Persona(
        name="Elad Gil",
        emoji="🟤",
        tagline="Execution at Scale",
        philosophy="Market timing and operational execution under scaling constraints.",
    ),
    Persona(
        name="Fred Wilson",
        emoji="🟢",
        tagline="Network Effects",
        philosophy="Community and compounding network defensibility.",
    ),
    Persona(
        name="Arjun Sethi",
        emoji="⚫",
        tagline="Data Signals",
        philosophy="Retention cohorts and quantitative PMF proof over narrative.",
    ),
    Persona(
        name="Reid Hoffman",
        emoji="🔷",
        tagline="Blitzscaling",
        philosophy="Speed in uncertain winner-take-most markets.",
    ),
    Persona(
        name="Sam Altman",
        emoji="🌐",
        tagline="Ambition Filter",
        philosophy="World-scale ambition with hard technical defensibility.",
    ),
    Persona(
        name="Garry Tan",
        emoji="🟡",
        tagline="Founder Empathy",
        philosophy="Founder-market fit and anti-mimetic opportunity spotting.",
    ),
    Persona(
        name="Naval Ravikant",
        emoji="🧘",
        tagline="Leverage and Compounding",
        philosophy="Specific knowledge plus scalable leverage and long compounding.",
    ),
    Persona(
        name="Paul Graham",
        emoji="🟠",
        tagline="Founder Craft",
        philosophy="Founder quality and non-scalable tactics that unlock early PMF.",
    ),
    Persona(
        name="Clayton Christensen",
        emoji="📘",
        tagline="Disruption Theory",
        philosophy="Jobs-to-be-done and disruptive entry from underserved segments.",
    ),
    Persona(
        name="Elon Musk",
        emoji="🚀",
        tagline="First Principles",
        philosophy="Physics and engineering constraints before market storytelling.",
    ),
    Persona(
        name="Thales Teixeira",
        emoji="📊",
        tagline="Customer Decoupling",
        philosophy="Customer value chain decoupling and capture points.",
    ),
    Persona(
        name="Vinod Khosla",
        emoji="🌿",
        tagline="Risk Appetite",
        philosophy="Asymmetric high-variance bets on technical discontinuities.",
    ),
    Persona(
        name="Masayoshi Son",
        emoji="💴",
        tagline="Scale Capital",
        philosophy="Aggressive capital deployment for global category dominance.",
    ),
]


def persona_roster() -> str:
    """Return a compact, numbered roster for prompt injection."""
    lines = []
    for idx, persona in enumerate(PERSONAS, start=1):
        lines.append(
            f"{idx}. {persona.emoji} {persona.name} — {persona.tagline}: {persona.philosophy}"
        )
    return "\n".join(lines)
