# AI VC Council - Vercel Service

Public web service version of the AI VC Council.

## Features

- Upload IR/Pitch deck PDF (Korean supported)
- Analyze startup website URL
- 16-member VC council simulation
- 4-stage output (memo, evaluations, debate, final IC recommendation)
- Korean/English output (`auto`, `ko`, `en`)

## Local run

```bash
cd ai_vc_council/vercel_service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY="your_api_key"
uvicorn api.analyze:app --reload --port 8000
```

Open `http://localhost:8000` for API health and `index.html` from a static server or Vercel preview.

## Deploy to Vercel

1. Push this folder to GitHub.
2. Import project in Vercel and set Root Directory to `ai_vc_council/vercel_service`.
3. Add environment variable:
- `OPENAI_API_KEY`: your server-side key
- Optional: `OPENAI_BASE_URL`
4. Deploy.

## Security notes

- This app uses your server-side OpenAI key. If public, add usage controls (auth, rate limit, quotas).
- Vercel function body limits apply; PDF uploads are practically capped around 4.5MB.
