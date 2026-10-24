# LensLearn 🔍

**Snap it. Ask it. Understand it.** LensLearn is a small multimodal learning assistant powered by **Gemma 4**, the open-weights model, through the Gemini API. Take or upload a photo of a textbook page, a plant leaf, a broken gadget, a label or a receipt, and get a plain-language answer in your own language.

Built for the MLH Hacktoberfest 2026 event in Kumasi.

## Features

- **Photo + text understanding.** Gemma 4 reads the image and your question together.
- **Four modes.**
  - *Explain*: what is this and why does it matter?
  - *Study*: summary, key terms and a 3-question quiz.
  - *Fix it*: numbered step-by-step help.
  - *Check*: careful description with honest uncertainty (not a diagnosis).
- **Local languages.** Replies in English, Twi, Ga, Ewe, Hausa, Dagbani, French, Spanish, Portuguese, Arabic or Swahili. Quality in lower-resource languages varies, so key English terms are added in brackets.
- **Follow-up questions.** Keep chatting about the same photo.
- **Phone-first.** Camera capture button, images are downscaled before upload so it works on slow 4G.

## Run it

You need Python 3.10+ and a free Gemini API key from <https://aistudio.google.com/apikey>.

```bash
git clone <your-repo-url> lenslearn
cd lenslearn
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env        # then paste your key into .env
python app.py
```

Open <http://localhost:5000>. To try it from your phone on the same Wi-Fi, open `http://<your-computer-ip>:5000`.

### Choose a Gemma 4 model

Set `GEMMA_MODEL` in `.env`:

| Model | Notes |
|---|---|
| `gemma-4-31b-it` | Default, strongest answers |
| `gemma-4-26b-a4b-it` | Lighter and faster |

## Deploy (e.g. DigitalOcean App Platform)

1. Push this repo to GitHub.
2. Create a new App Platform app from the repo.
3. Run command: `gunicorn app:app --bind 0.0.0.0:$PORT`
4. Add environment variable `GEMINI_API_KEY` (mark it secret).

## How it works

```
Browser ──(photo + question + mode + language)──▶ Flask /api/ask
                                                     │ resize + fix rotation (Pillow)
                                                     │ build instructions for the mode
                                                     ▼
                                          Gemma 4 via Gemini API (google-genai)
                                                     │
Browser ◀──────────── plain-language answer ─────────┘
```

Everything lives in two files: `app.py` (backend) and `static/index.html` (frontend, no build step).

## Responsible use

LensLearn can be wrong. The *Check* mode is designed to describe and suggest next steps, not diagnose. For health, safety or financial decisions, ask a qualified person.

## Contributing

Issues and pull requests are welcome. Good first ideas: more languages, saving past questions, a text-to-speech button, an offline mode using a local Gemma 4 build.

## License

MIT, see [LICENSE](LICENSE).
