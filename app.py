from __future__ import annotations

import os

import streamlit as st

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
from council.personas import PERSONAS


st.set_page_config(page_title="AI VC Council", layout="wide")

st.title("AI VC Council")
st.caption(
    "Upload a PDF IR deck or provide a startup webpage URL. The app runs a "
    "16-member simulated investment council and returns structured IC debate output."
)

with st.sidebar:
    st.header("Model Settings")
    api_key = st.text_input(
        "OPENAI_API_KEY",
        value=os.getenv("OPENAI_API_KEY", ""),
        type="password",
        help="Required for LLM calls.",
    )
    base_url = st.text_input(
        "OPENAI_BASE_URL (optional)",
        value=os.getenv("OPENAI_BASE_URL", ""),
        help="Use if routing through a compatible gateway.",
    )
    model = st.text_input("Model", value=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
    mode = st.selectbox(
        "Council Mode",
        options=["fast", "deep"],
        help=(
            "fast: 4 LLM calls total. deep: persona-by-persona Stage 2 (more expensive and slower)."
        ),
    )
    output_language = st.selectbox(
        "Output Language",
        options=["auto", "en", "ko"],
        help="auto detects from input text. Use ko for Korean output.",
    )
    temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.3, step=0.05)
    max_tokens = st.slider("Max tokens per call", min_value=1000, max_value=8000, value=4000, step=500)

    st.divider()
    st.subheader("Council Members")
    st.write(
        ", ".join(persona.name for persona in PERSONAS)
    )

col_left, col_right = st.columns([1.2, 1])

with col_left:
    company_name = st.text_input("Startup Name (optional)")
    deck_file = st.file_uploader("Upload IR/Pitch Deck (PDF)", type=["pdf"])
    webpage_url = st.text_input(
        "Startup Webpage URL (optional)",
        placeholder="https://example.com",
    )
    additional_notes = st.text_area(
        "Additional context (optional)",
        placeholder="Anything not in the deck/webpage that you want the council to consider.",
        height=140,
    )

    run_clicked = st.button("Run AI VC Council", type="primary", use_container_width=True)

with col_right:
    st.markdown("### What You Get")
    st.markdown(
        "- Stage 1: Deal memo extraction\n"
        "- Stage 2: 16 independent persona evaluations\n"
        "- Stage 3: 5-round Bull/Bear/Wild Card debate\n"
        "- Stage 4: final IC output with risks, diligence, and action plan"
    )
    st.info(
        "This is a strategy simulation tool. Outputs are not investment advice and do not represent real individuals' current views."
    )


if run_clicked:
    if not api_key.strip():
        st.error("OPENAI_API_KEY is required.")
        st.stop()

    status = st.status("Preparing startup input", expanded=True)

    try:
        deck_text = None
        if deck_file is not None:
            status.write("Extracting text from uploaded PDF deck")
            deck_text = extract_text_from_pdf_bytes(deck_file.getvalue())

        webpage_text = None
        if webpage_url.strip():
            status.write("Fetching and extracting text from startup webpage")
            webpage_text = extract_text_from_url(webpage_url.strip())

        startup_context = build_startup_context(
            deck_text=deck_text,
            webpage_text=webpage_text,
            additional_notes=additional_notes,
        )

        status.write("Connecting to LLM provider")
        client = OpenAIChatClient(
            api_key=api_key.strip(),
            base_url=base_url.strip() or None,
        )

        run_config = CouncilRunConfig(
            model=model.strip(),
            temperature=temperature,
            max_tokens=max_tokens,
            mode=mode,
            output_language=output_language,
        )

        def on_progress(stage: str, message: str) -> None:
            status.write(f"[{stage}] {message}")

        status.write("Running 4-stage VC council workflow")
        result = run_council_analysis(
            startup_context=startup_context,
            llm_client=client,
            config=run_config,
            company_name=company_name.strip() or None,
            progress=on_progress,
        )

        status.update(label="Council analysis complete", state="complete", expanded=False)

        st.success("Analysis generated successfully")

        tabs = st.tabs(["Full Report", "Stage 1", "Stage 2", "Stage 3", "Stage 4", "Input Context"])
        tabs[0].markdown(result.full_markdown)
        tabs[1].markdown(result.stage_1)
        tabs[2].markdown(result.stage_2)
        tabs[3].markdown(result.stage_3)
        tabs[4].markdown(result.stage_4)
        tabs[5].text(startup_context)

        st.download_button(
            label="Download report (.md)",
            data=result.full_markdown,
            file_name="vc_council_report.md",
            mime="text/markdown",
            use_container_width=True,
        )

    except (IngestionError, LLMClientError) as exc:
        status.update(label="Run failed", state="error", expanded=True)
        st.error(str(exc))
    except Exception as exc:  # pragma: no cover - UI fallback
        status.update(label="Run failed", state="error", expanded=True)
        st.error(f"Unexpected error: {exc}")
