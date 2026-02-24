from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

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

MAX_UPLOAD_BYTES = 4_500_000
ALLOWED_MODES = {"fast", "deep"}
ALLOWED_LANGUAGES = {"auto", "en", "ko"}
DEFAULT_ALLOWED_MODELS = {"gpt-4.1-mini", "gpt-4.1"}


def _load_allowed_models() -> set[str]:
    raw = os.getenv("ALLOWED_MODELS", "").strip()
    if not raw:
        return DEFAULT_ALLOWED_MODELS
    parsed = {item.strip() for item in raw.split(",") if item.strip()}
    return parsed or DEFAULT_ALLOWED_MODELS

app = FastAPI(title="AI VC Council")
ROOT_DIR = Path(__file__).resolve().parent


@app.get("/")
def web() -> FileResponse:
    return FileResponse(ROOT_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai-vc-council"}


@app.post("/api/analyze")
async def analyze(
    company_name: Optional[str] = Form(default=None),
    website_url: Optional[str] = Form(default=None),
    notes: Optional[str] = Form(default=None),
    mode: str = Form(default="fast"),
    language: str = Form(default="auto"),
    model: str = Form(default="gpt-4.1-mini"),
    temperature: float = Form(default=0.3),
    max_tokens: int = Form(default=4000),
    deck_file: Optional[UploadFile] = File(default=None),
) -> JSONResponse:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Server is missing OPENAI_API_KEY. Configure it in Vercel project settings.",
        )

    requested_mode = mode.strip().lower()
    if requested_mode not in ALLOWED_MODES:
        raise HTTPException(status_code=400, detail=f"mode must be one of {sorted(ALLOWED_MODES)}")

    language = language.strip().lower()
    if language not in ALLOWED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"language must be one of {sorted(ALLOWED_LANGUAGES)}",
        )

    requested_model = model.strip() or "gpt-4.1-mini"
    normalized_model = requested_model
    allowed_models = _load_allowed_models()
    model_fallback_note = ""
    if normalized_model not in allowed_models:
        if normalized_model.startswith("gpt-5"):
            normalized_model = "gpt-4.1-mini"
            model_fallback_note = (
                f"Model '{requested_model}' is not enabled for this endpoint. "
                "Auto-switched to gpt-4.1-mini."
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=(
                    "model is not allowed. Allowed models: "
                    + ", ".join(sorted(allowed_models))
                ),
            )

    if max_tokens < 1000 or max_tokens > 8000:
        raise HTTPException(status_code=400, detail="max_tokens must be between 1000 and 8000")

    if temperature < 0 or temperature > 1:
        raise HTTPException(status_code=400, detail="temperature must be between 0 and 1")

    effective_mode = requested_mode
    fallback_note = ""
    if requested_mode == "deep" and normalized_model.startswith("gpt-5"):
        effective_mode = "fast"
        fallback_note = (
            "Deep mode with gpt-5 models is auto-switched to fast mode to avoid "
            "serverless timeout."
        )

    # Cost and timeout guardrails for a public endpoint.
    if normalized_model.startswith("gpt-5"):
        token_cap = 2500
    else:
        token_cap = 4000 if effective_mode == "deep" else 6000
    effective_max_tokens = min(max_tokens, token_cap)

    try:
        deck_text: Optional[str] = None
        if deck_file is not None:
            raw = await deck_file.read()
            if len(raw) > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=(
                        "PDF file too large for Vercel function body limits. Keep it under ~4.5MB "
                        "or share a webpage URL instead."
                    ),
                )
            deck_text = extract_text_from_pdf_bytes(raw)

        webpage_text: Optional[str] = None
        if website_url and website_url.strip():
            webpage_text = extract_text_from_url(website_url.strip())

        startup_context = build_startup_context(
            deck_text=deck_text,
            webpage_text=webpage_text,
            additional_notes=notes,
        )

        client = OpenAIChatClient(api_key=api_key, base_url=os.getenv("OPENAI_BASE_URL"))
        result = run_council_analysis(
            startup_context=startup_context,
            llm_client=client,
            config=CouncilRunConfig(
                model=normalized_model,
                mode=effective_mode,
                output_language=language,
                temperature=temperature,
                max_tokens=effective_max_tokens,
            ),
            company_name=(company_name or "").strip() or None,
            progress=None,
        )

        payload: dict[str, Any] = {
            "ok": True,
            "requested_mode": requested_mode,
            "mode": effective_mode,
            "language": language,
            "requested_model": requested_model,
            "model": normalized_model,
            "requested_max_tokens": max_tokens,
            "effective_max_tokens": effective_max_tokens,
            "note": (
                model_fallback_note
                or fallback_note
                or (
                    "Deep mode applies internal per-stage token caps to reduce Vercel timeout risk."
                    if effective_mode == "deep"
                    else ""
                )
            ),
            "result": {
                "stage_1": result.stage_1,
                "stage_2": result.stage_2,
                "stage_3": result.stage_3,
                "stage_4": result.stage_4,
                "full_markdown": result.full_markdown,
            },
        }
        return JSONResponse(payload)
    except HTTPException:
        raise
    except (IngestionError, LLMClientError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc
