# AI VC Council

A runnable AI investment-committee app inspired by the AIVC prompt structure, customized to a 16-member VC council:

- Peter Thiel
- Marc Andreessen
- Bill Gurley
- Elad Gil
- Fred Wilson
- Arjun Sethi
- Reid Hoffman
- Sam Altman
- Garry Tan
- Naval Ravikant
- Paul Graham
- Clayton Christensen
- Elon Musk
- Thales Teixeira
- Vinod Khosla
- Masayoshi Son

## What it does

1. Ingests startup input from:
- Uploaded PDF IR/pitch deck
- Public startup webpage URL
- Optional extra notes
- Korean decks supported (auto language detection + Korean output option)

2. Runs a 4-stage AI council workflow:
- Stage 1: Deal memo extraction
- Stage 2: 16 persona evaluations
- Stage 3: 5-round Bull/Bear/Wild Card debate
- Stage 4: Final IC output (vote summary, risks, diligence, 30/90/180 plan)

3. Displays and exports a full markdown report.

## Quick start

```bash
cd ai_vc_council
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
export OPENAI_API_KEY="your_api_key_here"
streamlit run app.py
```

Then open the local URL shown by Streamlit.

## CLI usage

You can also run without UI:

```bash
cd ai_vc_council
export OPENAI_API_KEY="your_api_key_here"
python3 cli.py --company "Example AI" --pdf ./deck.pdf --url https://example.com --mode fast --out report.md
```

## Notes

- `fast` mode uses fewer model calls and is cheaper.
- `deep` mode runs persona-by-persona evaluations in Stage 2 and costs more.
- `Output Language` can be `auto`, `en`, or `ko`. `auto` detects Korean input.
- PDF extraction uses `pypdf` and a PyMuPDF fallback for better Korean text handling.
- PDF extraction is text-based; image-only decks need OCR first.
- This tool is for analytical simulation, not investment advice.

## Public deploy (GitHub + Vercel)

A Vercel-ready public web service version is in `ai_vc_council/vercel_service`.

- UI: `ai_vc_council/vercel_service/index.html`
- API: `ai_vc_council/vercel_service/api/analyze.py`
- Deployment guide: `ai_vc_council/vercel_service/README.md`
