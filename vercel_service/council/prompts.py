"""Prompt templates for the multi-stage VC council workflow."""

from __future__ import annotations

from council.personas import Persona, persona_roster


SYSTEM_PROMPT = """You are VC Council Agent, a rigorous venture investment committee simulator.

Core rules:
- Treat all personas as simulation lenses, not real people giving current advice.
- Never fabricate external facts. If unknown, write "Unknown" and list assumptions.
- Keep output decision-oriented with explicit tradeoffs.
- Separate facts from assumptions where relevant.
- Stay consistent with requested output format.
"""


def _language_instruction(output_language: str) -> str:
    if output_language == "ko":
        return (
            "Write the response in Korean. Keep proper nouns and framework names in English "
            "when needed (e.g., TAM/SAM/SOM, LTV/CAC)."
        )
    return "Write the response in English."


def stage_1_prompt(
    startup_context: str,
    company_name: str | None = None,
    output_language: str = "en",
) -> str:
    name = company_name.strip() if company_name else "Unknown Startup"
    language_instruction = _language_instruction(output_language)
    return f"""Analyze the startup input and produce Stage 1 output.

Company name hint: {name}
Language rule: {language_instruction}

Startup input:
{startup_context}

Output exactly in markdown with these sections:

## Stage 1 - Deal Memo
### Company Snapshot
- Problem:
- Solution:
- Customer:
- Business Model:
- Stage:

### Market View
- TAM:
- SAM:
- SOM:
- Notes on market dynamics:

### Traction
- Revenue / Growth:
- Product Usage / Retention:
- GTM Signals:

### Team
- Strengths:
- Gaps:

### Competition
- Key alternatives:
- Differentiation:

### Debate Triggers
- Provide 5 to 8 sharp questions that should cause disagreement inside an IC.

### Missing Data
- List missing information required before an investment decision.
"""


def stage_2_fast_prompt(stage_1_markdown: str, output_language: str = "en") -> str:
    roster = persona_roster()
    language_instruction = _language_instruction(output_language)
    return f"""Using Stage 1 output below, run Stage 2 independent evaluation for all 16 personas.

Stage 1 input:
{stage_1_markdown}

Persona roster (must use all exactly once):
{roster}

Language rule: {language_instruction}

Output exactly in markdown:

## Stage 2 - Independent Evaluations
For each persona, include:
- Verdict: Invest / Pass / Dig Deeper
- Strengths: 2 bullets
- Concerns: 2 bullets
- Killer Diligence Question: 1 bullet
- Confidence (0-100): 1 number

Then include:

### Vote Tally
- Invest:
- Pass:
- Dig Deeper:

### Suggested Debate Panel
- Bull: [Name] - one-line reason
- Bear: [Name] - one-line reason
- Wild Card: [Name] - one-line reason

Keep each persona section concise and concrete.
"""


def stage_2_deep_prompt(
    stage_1_markdown: str, persona: Persona, output_language: str = "en"
) -> str:
    language_instruction = _language_instruction(output_language)
    return f"""You are evaluating as one persona only.

Persona: {persona.emoji} {persona.name} - {persona.tagline}
Persona philosophy: {persona.philosophy}
Language rule: {language_instruction}

Stage 1 input:
{stage_1_markdown}

Output markdown only with this exact structure:

### {persona.emoji} {persona.name} - {persona.tagline}
- Verdict: Invest / Pass / Dig Deeper
- Strengths:
  - ...
  - ...
- Concerns:
  - ...
  - ...
- Killer Diligence Question:
  - ...
- Confidence (0-100): [number]
"""


def stage_2_panel_selection_prompt(
    stage_1_markdown: str, stage_2_markdown: str, output_language: str = "en"
) -> str:
    language_instruction = _language_instruction(output_language)
    return f"""Given Stage 1 and Stage 2 outputs, pick the best debate panel.

Stage 1:
{stage_1_markdown}

Stage 2:
{stage_2_markdown}

Language rule: {language_instruction}

Return only markdown:

### Suggested Debate Panel
- Bull: [Name] - one-line reason
- Bear: [Name] - one-line reason
- Wild Card: [Name] - one-line reason
"""


def stage_3_prompt(
    stage_1_markdown: str,
    stage_2_markdown: str,
    panel_markdown: str,
    output_language: str = "en",
) -> str:
    language_instruction = _language_instruction(output_language)
    return f"""Run Stage 3 IC debate using the material below.

Stage 1:
{stage_1_markdown}

Stage 2:
{stage_2_markdown}

Panel selection:
{panel_markdown}

Language rule: {language_instruction}

Output markdown:

## Stage 3 - IC Debate (5 Rounds)
For each round include exactly 3 speakers and have them rebut prior points:
- Bull:
- Bear:
- Wild Card:

Round objectives:
1) Initial theses and assumptions
2) Evidence clash (metrics, market logic, precedent)
3) Assumption stress test
4) Convergence and conditions
5) Final votes with explicit conditions

After round 5 include:

### Role Final Votes
- Bull: Invest / Pass / Dig Deeper - one-line rationale
- Bear: Invest / Pass / Dig Deeper - one-line rationale
- Wild Card: Invest / Pass / Dig Deeper - one-line rationale
"""


def stage_4_prompt(
    stage_1_markdown: str,
    stage_2_markdown: str,
    stage_3_markdown: str,
    output_language: str = "en",
) -> str:
    language_instruction = _language_instruction(output_language)
    return f"""Produce Stage 4 final report.

Inputs:
Stage 1:
{stage_1_markdown}

Stage 2:
{stage_2_markdown}

Stage 3:
{stage_3_markdown}

Language rule: {language_instruction}

Output markdown with this exact order:

## Stage 4 - Final IC Output
### Final Vote Summary
- Invest:
- Pass:
- Dig Deeper:

### Conviction
- Level: High / Medium / Low
- Why:

### Top 5 Risks and Mitigations
1. Risk - mitigation experiment
2. ...
3. ...
4. ...
5. ...

### Diligence Checklist (10)
1. ...
2. ...
3. ...
4. ...
5. ...
6. ...
7. ...
8. ...
9. ...
10. ...

### 30/90/180 Day Founder Plan
- 30 days:
- 90 days:
- 180 days:

### Executive Recommendation
- 1 concise paragraph with recommendation and explicit conditions.
"""


def stage_34_fast_prompt(
    stage_1_markdown: str,
    stage_2_markdown: str,
    panel_markdown: str,
    output_language: str = "en",
) -> str:
    language_instruction = _language_instruction(output_language)
    return f"""Produce both Stage 3 debate and Stage 4 final recommendation in one response.

Inputs:
Stage 1:
{stage_1_markdown}

Stage 2:
{stage_2_markdown}

Panel selection:
{panel_markdown}

Language rule: {language_instruction}

Output markdown in this exact order:

## Stage 3 - IC Debate (5 Rounds)
For each round include exactly 3 speakers and have them rebut prior points:
- Bull:
- Bear:
- Wild Card:

Round objectives:
1) Initial theses and assumptions
2) Evidence clash (metrics, market logic, precedent)
3) Assumption stress test
4) Convergence and conditions
5) Final votes with explicit conditions

After round 5 include:

### Role Final Votes
- Bull: Invest / Pass / Dig Deeper - one-line rationale
- Bear: Invest / Pass / Dig Deeper - one-line rationale
- Wild Card: Invest / Pass / Dig Deeper - one-line rationale

## Stage 4 - Final IC Output
### Final Vote Summary
- Invest:
- Pass:
- Dig Deeper:

### Conviction
- Level: High / Medium / Low
- Why:

### Top 5 Risks and Mitigations
1. Risk - mitigation experiment
2. ...
3. ...
4. ...
5. ...

### Diligence Checklist (10)
1. ...
2. ...
3. ...
4. ...
5. ...
6. ...
7. ...
8. ...
9. ...
10. ...

### 30/90/180 Day Founder Plan
- 30 days:
- 90 days:
- 180 days:

### Executive Recommendation
- 1 concise paragraph with recommendation and explicit conditions.
"""
