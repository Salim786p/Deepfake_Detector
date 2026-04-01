# Fake Content Detection Assistant

Chrome extension + FastAPI backend for image deepfake and synthetic media detection.

## Architecture

- Chrome Extension right-click flow in `extension/`
- FastAPI backend in `backend/`
- LangGraph orchestration in `backend/app/graph.py`
- Sightengine for `genai` + `deepfake` scoring
- Gemini Vision for visual explanation

## Run the backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Load the extension

1. Open Chrome and go to `chrome://extensions`
2. Enable `Developer mode`
3. Click `Load unpacked`
4. Select the `extension/` folder
5. Right-click any web image and choose `Analyze image for fake/manipulated content`
6. Open the extension popup to view the result

## Notes

- The extension defaults to `http://127.0.0.1:8000`
- You can change the backend URL from the popup
- Sightengine is used as the detection signal and Gemini provides the visual explanation layer
