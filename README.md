# HealthGuard AI

AI-powered WhatsApp health misinformation checker. Paste a message, upload a screenshot, or speak it — the app cross-checks it against WHO/ICMR/MoHFW-aligned guidance using Groq's `llama-3.3-70b-versatile` and returns a verdict, confidence score, explanation, and a ready-to-forward safe reply.

## ⚠️ First: rotate your Groq API key

The key that was in your old `.env` was shared in plain text and should be treated as compromised. Go to the Groq console, revoke it, and generate a new one before using this.

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Install Tesseract OCR (needed for the screenshot feature):
- **Windows:** https://github.com/UB-Mannheim/tesseract/wiki — then set `TESSERACT_CMD` in `.env` to the install path.
- **Mac:** `brew install tesseract`
- **Linux:** `sudo apt install tesseract-ocr`

Then:
```bash
cp .env.example .env
```
Open `.env` and paste in your **new** Groq API key.

## Run

```bash
python app.py
```

Visit `http://127.0.0.1:5000`.

## What changed from the original prototype

- `requirements.txt` now matches what `app.py` actually imports (was listing `google-genai` instead of `groq`)
- Tesseract path is no longer hardcoded to a Windows-only location — it reads `TESSERACT_CMD` from `.env`, or auto-detects `tesseract` on PATH
- Added `prompt/system_prompt.txt`, which the app expected but didn't include — it instructs the model to return strict JSON (`verdict`, `confidence`, `explanation`, `sources`, `safe_reply`) so the frontend dashboard has real structured data to render, not just a raw text blob
- `/verify` now parses and validates that JSON, with clear error responses if the model output can't be parsed
- `templates/index.html` is the redesigned dashboard UI, wired to real `/verify` and `/upload` calls (screenshot OCR and voice input via the browser's Speech Recognition API both work end-to-end)
- Claims-checked / false-claims stats update live as people use the tool (in-memory — resets on server restart; swap in a database for persistence)
- `.gitignore` now actually excludes `.env` and Python build artifacts
