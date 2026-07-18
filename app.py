"""
Symptom-Checker Web App (Flask backend) — Gemini version
==========================================================
Public-facing web version of the symptom-checker agent, now powered by
Google's Gemini API instead of Anthropic's.

Run locally:
    pip install -r requirements.txt --break-system-packages
    export GEMINI_API_KEY=...
    python3 app.py
    -> open http://localhost:5000

Get a free API key: https://aistudio.google.com/apikey
Deploy: see DEPLOY.md
"""

import os
import json
from flask import Flask, request, jsonify, render_template
from google import genai
from google.genai import types

app = Flask(__name__)

MODEL = "gemini-3.5-flash"  # fast, free-tier friendly default

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("FATAL: GEMINI_API_KEY environment variable is not set.")
client = genai.Client(api_key=API_KEY) if API_KEY else None

RED_FLAG_KEYWORDS = [
    "chest pain", "difficulty breathing", "shortness of breath",
    "can't breathe", "cannot breathe", "severe bleeding", "unconscious",
    "unresponsive", "stroke", "slurred speech", "face drooping",
    "one side weakness", "severe head injury", "suicidal", "suicide",
    "overdose", "poisoning", "seizure", "not breathing", "blue lips",
    "severe allergic reaction", "anaphylaxis", "coughing blood",
    "vomiting blood", "worst headache of my life",
]

SYSTEM_PROMPT = """You are a cautious medical symptom-information assistant. You are NOT a doctor and must never present your output as a diagnosis.

Rules you must always follow:
1. Never say "you have X". Always phrase as "possible causes include X, Y, Z" with rough likelihood (common / less common / rare).
2. Always include an urgency/risk level: LOW, MODERATE, or HIGH.
3. If symptoms could plausibly indicate anything dangerous, err toward a higher urgency rating.
4. Ask at most 3 concise follow-up questions if the description is too vague (duration, severity, associated symptoms, relevant history).
5. Never suggest specific drug dosages or prescription medications.
6. Always end with a recommendation to consult a licensed healthcare professional, specifying urgency.
7. Respond ONLY in valid JSON matching this schema, nothing else, no markdown fences:
{
  "needs_more_info": bool,
  "follow_up_questions": [string],
  "possible_causes": [{"condition": string, "likelihood": "common"|"less common"|"rare", "why": string}],
  "urgency": "LOW"|"MODERATE"|"HIGH",
  "recommendation": string
}
"""


def check_red_flags(text: str):
    text_lower = text.lower()
    return [kw for kw in RED_FLAG_KEYWORDS if kw in text_lower]


def to_gemini_contents(conversation):
    """Convert our {role: user/assistant, content: str} list into
    Gemini's {role: user/model, parts: [...]} format."""
    contents = []
    for turn in conversation:
        role = "model" if turn["role"] == "assistant" else "user"
        contents.append(
            types.Content(role=role, parts=[types.Part(text=turn["content"])])
        )
    return contents


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json(force=True)
    conversation = data.get("conversation", [])
    if not conversation:
        return jsonify({"error": "empty conversation"}), 400

    last_user_msg = conversation[-1]["content"]

    # Deterministic safety check runs before any model call
    matched = check_red_flags(last_user_msg)
    if matched:
        return jsonify({
            "emergency": True,
            "matched_keywords": matched,
        })

    if client is None:
        return jsonify({"error": "Server misconfigured: GEMINI_API_KEY is not set."}), 500

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=to_gemini_contents(conversation),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                max_output_tokens=2048,
                safety_settings=[
                    types.SafetySetting(
                        category="HARM_CATEGORY_DANGEROUS_CONTENT",
                        threshold="BLOCK_ONLY_HIGH",
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_HARASSMENT",
                        threshold="BLOCK_ONLY_HIGH",
                    ),
                ],
            ),
        )

        # Check for truncation or a safety block before trying to parse
        candidate = response.candidates[0] if response.candidates else None
        finish_reason = getattr(candidate, "finish_reason", None) if candidate else None
        raw = response.text.strip() if response.text else ""

        if not raw:
            print(f"EMPTY RESPONSE — finish_reason={finish_reason}, full response: {response}")
            return jsonify({"error": f"Model returned no text (finish_reason={finish_reason}). This can happen when the safety filter blocks a response — try rephrasing."}), 500

        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        result["emergency"] = False
        return jsonify(result)
    except json.JSONDecodeError:
        print(f"JSON PARSE FAILED. Raw model output was: {raw!r}")
        return jsonify({
            "emergency": False,
            "needs_more_info": False,
            "possible_causes": [],
            "urgency": "MODERATE",
            "recommendation": "Could not process that — please consult a doctor directly.",
        })
    except Exception as e:
        import traceback
        traceback.print_exc()  # shows full error in Render logs
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
