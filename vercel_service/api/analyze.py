from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

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

app = FastAPI(title="AI VC Council API")


@app.get("/")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai-vc-council"}


@app.post("/")
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

    mode = mode.strip().lower()
    if mode not in ALLOWED_MODES:
        raise HTTPException(status_code=400, detail=f"mode must be one of {sorted(ALLOWED_MODES)}")

    language = language.strip().lower()
    if language not in ALLOWED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"language must be one of {sorted(ALLOWED_LANGUAGES)}",
        )

    if max_tokens < 1000 or max_tokens > 8000:
        raise HTTPException(status_code=400, detail="max_tokens must be between 1000 and 8000")

    if temperature < 0 or temperature > 1:
        raise HTTPException(status_code=400, detail="temperature must be between 0 and 1")

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
                model=model.strip() or "gpt-4.1-mini",
                mode=mode,
                output_language=language,
                temperature=temperature,
                max_tokens=max_tokens,
            ),
            company_name=(company_name or "").strip() or None,
            progress=None,
        )

        payload: dict[str, Any] = {
            "ok": True,
            "mode": mode,
            "language": language,
            "model": model,
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
