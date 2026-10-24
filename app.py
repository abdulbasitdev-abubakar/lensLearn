"""LensLearn: snap a photo, ask about it, learn from it.

A tiny Flask backend that sends an image plus a question to Gemma 4
through the Gemini API and returns a plain-language answer.
"""

import io
import json
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from google import genai
from google.genai import types
from PIL import Image, ImageOps

load_dotenv()

API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = os.environ.get("GEMMA_MODEL", "gemma-4-31b-it")
MAX_SIDE = 1568  # downscale big phone photos so uploads stay fast on 4G
MAX_UPLOAD_MB = 12

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

_client = None


def client():
    global _client
    if _client is None:
        if not API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        _client = genai.Client(api_key=API_KEY)
    return _client


MODES = {
    "explain": (
        "Explain what is in the image in simple, clear language. Say what it is, "
        "how it works or why it matters, and one interesting fact. Keep it short "
        "and friendly, like a patient teacher."
    ),
    "study": (
        "Turn what is in the image into study help. Give: (1) a 3-5 bullet summary "
        "of the key ideas, (2) the important terms with one-line definitions, and "
        "(3) a 3-question quiz with the answers listed at the very end."
    ),
    "steps": (
        "The image shows a problem, task, or something broken or confusing. Give "
        "practical step-by-step help to solve or fix it. Number the steps, mention "
        "safety if relevant, and say when to ask a professional."
    ),
    "check": (
        "The image shows something that may need a careful look (a plant leaf, a "
        "food item, a label, a document, a receipt). Describe what you can actually "
        "see, list likely explanations, and suggest sensible next steps. Be honest "
        "about uncertainty and never present your answer as a professional "
        "diagnosis."
    ),
}

BASE_RULES = (
    "You are LensLearn, a friendly learning assistant for students and community "
    "members. Use short sentences, everyday words, and simple formatting (short "
    "paragraphs, '-' bullets, **bold** for key terms). Only describe what you can "
    "genuinely see; if the image is unclear, say so and ask for a better photo. "
)


def build_instructions(mode: str, language: str) -> str:
    task = MODES.get(mode, MODES["explain"])
    lang = (
        f"Reply in {language}. If you are less sure in {language}, keep sentences "
        "very simple and put the key English terms in brackets."
        if language and language.lower() != "english"
        else "Reply in English."
    )
    return f"{BASE_RULES}\n\nTask: {task}\n\n{lang}"


def prepare_image(file_storage):
    """Fix phone-camera rotation, shrink, and re-encode as JPEG bytes."""
    img = Image.open(file_storage.stream)
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/health")
def health():
    return jsonify(ok=True, model=MODEL, key_configured=bool(API_KEY))


@app.post("/api/ask")
def ask():
    mode = request.form.get("mode", "explain")
    language = request.form.get("language", "English")
    question = (request.form.get("question") or "").strip()

    try:
        history = json.loads(request.form.get("history") or "[]")
    except json.JSONDecodeError:
        return jsonify(error="Bad conversation history."), 400

    image_part = None
    upload = request.files.get("image")
    if upload and upload.filename:
        try:
            image_part = types.Part.from_bytes(
                data=prepare_image(upload), mime_type="image/jpeg"
            )
        except Exception:
            return jsonify(error="That file doesn't look like a valid image."), 400

    if not image_part and not question:
        return jsonify(error="Add a photo or type a question."), 400

    instructions = build_instructions(mode, language)

    # Build the conversation. Instructions + image ride on the first user turn
    # so follow-up questions keep their context.
    turns = [(m.get("role"), (m.get("text") or "")) for m in history][-10:]
    turns.append(("user", question or "Please help me with this image."))

    contents = []
    for i, (role, text) in enumerate(turns):
        parts = []
        if i == 0:
            if image_part:
                parts.append(image_part)
            if role == "user":
                text = f"{instructions}\n\nUser: {text}"
        parts.append(types.Part.from_text(text=text))
        contents.append(
            types.Content(role="user" if role == "user" else "model", parts=parts)
        )

    try:
        response = client().models.generate_content(model=MODEL, contents=contents)
        answer = (response.text or "").strip()
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 500
    except Exception as exc:  # network, quota, safety blocks, etc.
        app.logger.exception("Gemma call failed")
        msg = str(exc)
        if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
            return jsonify(error="Rate limit reached. Wait a moment and try again."), 429
        return jsonify(error="The model couldn't answer that. Try again."), 502

    if not answer:
        return jsonify(error="The model returned an empty answer. Try rephrasing."), 502
    return jsonify(answer=answer, model=MODEL)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
