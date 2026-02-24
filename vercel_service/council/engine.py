"""Council orchestration engine."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from dataclasses import dataclass
from typing import Callable

from council.language import output_language_label, resolve_output_language
from council.llm_client import LLMConfig, OpenAIChatClient
from council.personas import PERSONAS
from council.prompts import (
    SYSTEM_PROMPT,
    stage_34_fast_prompt,
    stage_1_prompt,
    stage_2_deep_prompt,
    stage_2_fast_prompt,
    stage_2_panel_selection_prompt,
    stage_3_prompt,
    stage_4_prompt,
)

ProgressCallback = Callable[[str, str], None]

DEEP_STAGE1_TOKEN_CAP = 3200
DEEP_PERSONA_TOKEN_CAP = 1200
DEEP_PANEL_TOKEN_CAP = 800
DEEP_DEBATE_TOKEN_CAP = 2200
DEEP_FINAL_TOKEN_CAP = 2200
DEEP_PERSONA_WORKERS = 4

FAST_STAGE1_TOKEN_CAP = 1800
FAST_STAGE2_TOKEN_CAP = 1400
FAST_STAGE4_TOKEN_CAP = 1400
FAST_STAGE34_TOKEN_CAP = 2000

DEEP_STAGE1_INPUT_CHAR_CAP = 60_000
FAST_STAGE1_INPUT_CHAR_CAP = 28_000


@dataclass(frozen=True)
class CouncilRunConfig:
    model: str = "gpt-4.1-mini"
    temperature: float = 0.3
    max_tokens: int = 4000
    mode: str = "fast"  # fast | deep
    output_language: str = "auto"  # auto | en | ko


@dataclass(frozen=True)
class CouncilResult:
    stage_1: str
    stage_2: str
    stage_3: str
    stage_4: str

    @property
    def full_markdown(self) -> str:
        return (
            "# AI VC Council Result\n\n"
            f"{self.stage_1}\n\n"
            f"{self.stage_2}\n\n"
            f"{self.stage_3}\n\n"
            f"{self.stage_4}"
        )


def _trim_for_prompt(text: str, max_chars: int = 24_000) -> str:
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}\n\n[TRUNCATED FOR TOKEN SAFETY]"


def _extract_panel_block(stage_2_markdown: str) -> str | None:
    pattern = r"(### Suggested Debate Panel[\s\S]*)"
    match = re.search(pattern, stage_2_markdown)
    if not match:
        return None
    return match.group(1).strip()


def _notify(progress: ProgressCallback | None, stage: str, message: str) -> None:
    if progress:
        progress(stage, message)


def _build_cfg(base: CouncilRunConfig, max_tokens: int) -> LLMConfig:
    return LLMConfig(
        model=base.model,
        temperature=base.temperature,
        max_tokens=max_tokens,
    )


def _split_stage_34(markdown: str) -> tuple[str, str]:
    stage4_heading = "## Stage 4 - Final IC Output"
    idx = markdown.find(stage4_heading)
    if idx == -1:
        return markdown.strip(), ""
    return markdown[:idx].strip(), markdown[idx:].strip()


def run_council_analysis(
    *,
    startup_context: str,
    llm_client: OpenAIChatClient,
    config: CouncilRunConfig,
    company_name: str | None = None,
    progress: ProgressCallback | None = None,
) -> CouncilResult:
    mode = config.mode.lower().strip()
    requested_tokens = config.max_tokens

    resolved_language = resolve_output_language(config.output_language, startup_context)
    _notify(
        progress,
        "setup",
        f"Output language: {output_language_label(resolved_language)}",
    )

    if mode == "deep":
        stage1_cfg = _build_cfg(config, min(requested_tokens, DEEP_STAGE1_TOKEN_CAP))
        persona_cfg = _build_cfg(config, min(requested_tokens, DEEP_PERSONA_TOKEN_CAP))
        panel_cfg = _build_cfg(config, min(requested_tokens, DEEP_PANEL_TOKEN_CAP))
        stage3_cfg = _build_cfg(config, min(requested_tokens, DEEP_DEBATE_TOKEN_CAP))
        stage4_cfg = _build_cfg(config, min(requested_tokens, DEEP_FINAL_TOKEN_CAP))
        stage1_input_char_cap = DEEP_STAGE1_INPUT_CHAR_CAP
    else:
        stage1_cfg = _build_cfg(config, min(requested_tokens, FAST_STAGE1_TOKEN_CAP))
        persona_cfg = _build_cfg(config, min(requested_tokens, FAST_STAGE2_TOKEN_CAP))
        panel_cfg = _build_cfg(config, min(requested_tokens, FAST_STAGE2_TOKEN_CAP))
        stage34_cfg = _build_cfg(config, min(requested_tokens, FAST_STAGE34_TOKEN_CAP))
        stage4_cfg = _build_cfg(config, min(requested_tokens, FAST_STAGE4_TOKEN_CAP))
        stage1_input_char_cap = FAST_STAGE1_INPUT_CHAR_CAP

    _notify(progress, "stage_1", "Running Stage 1 deal memo extraction")
    stage_1 = llm_client.complete(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=stage_1_prompt(
            startup_context=_trim_for_prompt(startup_context, max_chars=stage1_input_char_cap),
            company_name=company_name,
            output_language=resolved_language,
        ),
        config=stage1_cfg,
    )

    _notify(progress, "stage_2", "Running Stage 2 independent evaluations")

    if mode == "deep":
        sections_by_name: dict[str, str] = {}
        max_workers = min(DEEP_PERSONA_WORKERS, len(PERSONAS))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {}
            for persona in PERSONAS:
                _notify(progress, "stage_2", f"Queued {persona.name}")
                future = executor.submit(
                    llm_client.complete,
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=stage_2_deep_prompt(
                        stage_1_markdown=_trim_for_prompt(stage_1),
                        persona=persona,
                        output_language=resolved_language,
                    ),
                    config=persona_cfg,
                )
                future_map[future] = persona.name

            for future in as_completed(future_map):
                persona_name = future_map[future]
                sections_by_name[persona_name] = future.result()
                _notify(progress, "stage_2", f"Completed {persona_name}")

        sections: list[str] = ["## Stage 2 - Independent Evaluations"]
        for persona in PERSONAS:
            sections.append(sections_by_name[persona.name])

        stage_2_core = "\n\n".join(sections)
        panel_block = llm_client.complete(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=stage_2_panel_selection_prompt(
                stage_1_markdown=_trim_for_prompt(stage_1),
                stage_2_markdown=_trim_for_prompt(stage_2_core),
                output_language=resolved_language,
            ),
            config=panel_cfg,
        )
        stage_2 = f"{stage_2_core}\n\n{panel_block}"
    else:
        stage_2 = llm_client.complete(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=stage_2_fast_prompt(
                stage_1_markdown=_trim_for_prompt(stage_1),
                output_language=resolved_language,
            ),
            config=persona_cfg,
        )
        panel_block = _extract_panel_block(stage_2)
        if panel_block is None:
            panel_block = llm_client.complete(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=stage_2_panel_selection_prompt(
                    stage_1_markdown=_trim_for_prompt(stage_1),
                    stage_2_markdown=_trim_for_prompt(stage_2),
                    output_language=resolved_language,
                ),
                config=panel_cfg,
            )

    if mode == "deep":
        _notify(progress, "stage_3", "Running Stage 3 debate")
        stage_3 = llm_client.complete(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=stage_3_prompt(
                stage_1_markdown=_trim_for_prompt(stage_1),
                stage_2_markdown=_trim_for_prompt(stage_2),
                panel_markdown=_trim_for_prompt(panel_block, max_chars=4_000),
                output_language=resolved_language,
            ),
            config=stage3_cfg,
        )

        _notify(progress, "stage_4", "Running Stage 4 final IC output")
        stage_4 = llm_client.complete(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=stage_4_prompt(
                stage_1_markdown=_trim_for_prompt(stage_1, max_chars=16_000),
                stage_2_markdown=_trim_for_prompt(stage_2, max_chars=20_000),
                stage_3_markdown=_trim_for_prompt(stage_3, max_chars=16_000),
                output_language=resolved_language,
            ),
            config=stage4_cfg,
        )
    else:
        _notify(progress, "stage_3", "Running combined Stage 3+4 synthesis")
        stage_34 = llm_client.complete(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=stage_34_fast_prompt(
                stage_1_markdown=_trim_for_prompt(stage_1),
                stage_2_markdown=_trim_for_prompt(stage_2),
                panel_markdown=_trim_for_prompt(panel_block, max_chars=4_000),
                output_language=resolved_language,
            ),
            config=stage34_cfg,
        )
        stage_3, stage_4 = _split_stage_34(stage_34)

        if not stage_4:
            _notify(progress, "stage_4", "Stage 4 missing, running fallback generation")
            stage_4 = llm_client.complete(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=stage_4_prompt(
                    stage_1_markdown=_trim_for_prompt(stage_1, max_chars=16_000),
                    stage_2_markdown=_trim_for_prompt(stage_2, max_chars=20_000),
                    stage_3_markdown=_trim_for_prompt(stage_3, max_chars=16_000),
                    output_language=resolved_language,
                ),
                config=stage4_cfg,
            )

    _notify(progress, "done", "Council run completed")
    return CouncilResult(stage_1=stage_1, stage_2=stage_2, stage_3=stage_3, stage_4=stage_4)
