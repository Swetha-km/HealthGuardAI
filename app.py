import os
import json
import shutil

from flask import Flask, render_template, request, jsonify
from groq import Groq
from dotenv import load_dotenv
import pytesseract
from PIL import Image

# ----------------------------
# Load Environment Variables
# ----------------------------
load_dotenv()
pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD")
import pytesseract
import os

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

app = Flask(__name__)

# ----------------------------
# Tesseract OCR Configuration
# ----------------------------
# Don't hardcode a machine-specific path. Instead:
# 1. Use TESSERACT_CMD from .env if the person set one (e.g. on Windows).
# 2. Otherwise, look for tesseract already on PATH (Linux/Mac/most hosts).
_tess_cmd = os.getenv("TESSERACT_CMD") or shutil.which("tesseract")
if _tess_cmd:
    pytesseract.pytesseract.tesseract_cmd = _tess_cmd
else:
    print(
        "WARNING: Tesseract not found on PATH and TESSERACT_CMD not set in .env. "
        "Screenshot upload will fail until this is configured."
    )

# ----------------------------
# Groq API Configuration
# ----------------------------
API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    print("WARNING: GROQ_API_KEY is not set. /verify will fail until it is added to .env.")

client = Groq(api_key=API_KEY) if API_KEY else None

# ----------------------------
# Load System Prompt
# ----------------------------
PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompt", "system_prompt.txt")
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    system_prompt = f.read()

STAT_COUNTERS = {
    "claims_checked": 128,
    "false_claims": 89,
}


def _strip_code_fences(text: str) -> str:
    """The model sometimes wraps JSON in ```json ... ``` even when told not to. Strip it."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def _parse_verdict(raw_text: str) -> dict:
    cleaned = _strip_code_fences(raw_text)
    data = json.loads(cleaned)

    # Defensive defaults in case the model omits a field despite instructions.
    return {
        "verdict": data.get("verdict", "caution"),
        "confidence": int(data.get("confidence", 50)),
        "risk_level": data.get("risk_level", "medium"),
        "category": data.get("category", "").strip(),
        "explanation": data.get("explanation", "").strip(),
        "sources": data.get("sources", []) or [],
        "medical_advice": data.get("medical_advice", "").strip(),
        "safe_reply": data.get("safe_reply", "").strip(),
    }


# ----------------------------
# Home Page
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html", stats=STAT_COUNTERS)


# ----------------------------
# Health Verification
# ----------------------------
@app.route("/verify", methods=["POST"])
def verify():
    if client is None:
        return jsonify({"error": "Server is missing GROQ_API_KEY. Add it to .env and restart."}), 500

    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "Please enter a health message."}), 400

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            temperature=0.3,
            max_tokens=600,
        )

        raw_result = response.choices[0].message.content

        try:
            result = _parse_verdict(raw_result)
        except (json.JSONDecodeError, ValueError) as parse_err:
            print("JSON PARSE ERROR:", repr(parse_err))
            print("RAW MODEL OUTPUT:", raw_result)
            return jsonify({
                "error": "AI response could not be parsed. Please try again."
            }), 502

        STAT_COUNTERS["claims_checked"] += 1
        if result["verdict"] == "false":
            STAT_COUNTERS["false_claims"] += 1

        result["claim"] = message
        result["stats"] = STAT_COUNTERS
        return jsonify(result)

    except Exception as e:
        print("GROQ ERROR:", repr(e))
        return jsonify({"error": "Verification service is temporarily unavailable."}), 500


# ----------------------------
# OCR Upload
# ----------------------------
@app.route("/upload", methods=["POST"])
def upload():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded."}), 400

    if not (os.getenv("TESSERACT_CMD") or shutil.which("tesseract")):
        return jsonify({"error": "OCR is not configured on this server."}), 500

    try:
        image_file = request.files["image"]
        img = Image.open(image_file)
        extracted_text = pytesseract.image_to_string(img).strip()

        if not extracted_text:
            return jsonify({"error": "Couldn't find readable text in that image."}), 422

        return jsonify({"text": extracted_text})

    except Exception as e:
        print("OCR ERROR:", repr(e))
        return jsonify({"error": "Could not read image."}), 500


# ----------------------------
# Run Application
# ----------------------------
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

