# Fake Content Detection Assistant Backend

## What it does

This FastAPI service accepts an image URL or file upload, runs a LangGraph pipeline, calls:

- Sightengine for `genai` and `deepfake` scores
- Gemini Vision for visual explanation

It then merges both into one final verdict JSON response.

## Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Fill in `.env` with your real API keys.

## Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints

- `GET /health`
- `POST /api/analyze-url`
- `POST /api/analyze-upload`

## Example request

```bash
curl -X POST "http://127.0.0.1:8000/api/analyze-url" ^
  -H "Content-Type: application/json" ^
  -d "{\"image_url\":\"https://example.com/image.jpg\"}"
```
