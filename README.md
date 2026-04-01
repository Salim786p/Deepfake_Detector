# Fake Content Detection Assistant

A Chrome extension and Python backend that help users inspect webpage images for possible AI generation, deepfakes, or manipulation. A user right-clicks an image in the browser, the image is analyzed by multiple services, and the result is shown in the extension popup with a verdict, confidence score, and explanation.

## Overview

This project combines:

- a Chrome Extension built with Manifest V3
- a FastAPI backend
- a LangGraph pipeline for orchestration
- Sightengine for AI-generated and deepfake scoring
- Gemini for visual explanation

The goal is to make image verification simple for end users while still keeping the backend modular and explainable.

## How It Works

1. The user right-clicks an image in Chrome.
2. The extension sends the image to the backend.
3. The backend runs a LangGraph workflow.
4. Sightengine returns synthetic image and deepfake risk scores.
5. Gemini reviews the image and produces a visual explanation.
6. The backend merges these results into one final verdict.
7. The extension popup displays the final analysis.

## Features

- Right-click image analysis from Chrome
- Deepfake and AI-generated risk scoring with Sightengine
- Visual explanation using Gemini
- FastAPI backend with clean JSON responses
- Fallback upload flow when some sites block direct image download
- Popup UI that shows verdict, confidence, explanation, and suggested next step

## Tech Stack

- Frontend Extension: HTML, CSS, JavaScript, Chrome Extensions API, Manifest V3
- Backend: Python, FastAPI, Uvicorn
- Orchestration: LangGraph
- AI Providers: Sightengine, Gemini API

## Repository Structure

```text
Detector/
|- backend/
|  |- app/
|  |  |- agents/
|  |  |- services/
|  |  |- tools/
|  |  |- config.py
|  |  |- graph.py
|  |  |- main.py
|  |  `- schemas.py
|  |- .env.example
|  |- README.md
|  `- requirements.txt
|- extension/
|  |- background.js
|  |- icon128.png
|  |- manifest.json
|  |- popup.css
|  |- popup.html
|  `- popup.js
`- README.md
```

## Prerequisites

Before running the project, make sure you have:

- Python 3.10 or newer
- Google Chrome
- internet access
- a Gemini API key
- Sightengine API credentials

## Getting API Keys

### Gemini API Key

Gemini is used for the vision explanation step.

Get it from:
- https://aistudio.google.com/

You will need:
- `GEMINI_API_KEY`

### Sightengine Credentials

Sightengine is used for AI-generated image and deepfake detection.

Get them from:
- https://sightengine.com/

You will need:
- `SIGHTENGINE_USER`
- `SIGHTENGINE_SECRET`

## Installation

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd Detector
```

### 2. Create the backend environment file

Move into the backend folder and copy the sample env file:

```powershell
cd backend
copy .env.example .env
```

Then open `backend/.env` and replace the placeholder values with your real credentials:

```env
GEMINI_API_KEY=your_real_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
SIGHTENGINE_USER=your_real_sightengine_user
SIGHTENGINE_SECRET=your_real_sightengine_secret
CORS_ORIGINS=*
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=info
```

Important:

- `backend/.env` contains secrets and must not be committed
- `backend/.env.example` should always keep placeholder values only

### 3. Create and activate a virtual environment

From the `backend` folder:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 4. Install backend dependencies

```powershell
pip install -r requirements.txt
```

## Running the Backend

From the `backend` folder:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

If the backend starts correctly, test it in your browser:

```text
http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "app_name": "Fake Content Detection Assistant"
}
```

## Loading the Chrome Extension

1. Open Chrome
2. Visit `chrome://extensions`
3. Enable `Developer mode`
4. Click `Load unpacked`
5. Select the `extension/` folder from this repository

After loading, Chrome will install the extension locally.

## Configuring the Extension

The extension expects the backend to run at:

```text
http://127.0.0.1:8000
```

That is already the default value in the popup. If your backend runs somewhere else, open the popup and update the backend URL there.

## How To Use

1. Open a webpage that contains an image
2. Right-click the image
3. Choose `Analyze image for fake/manipulated content`
4. Wait a few seconds
5. Open the extension popup
6. Review the verdict and explanation

The popup shows:

- final verdict
- confidence
- Sightengine AI-generated score
- Sightengine deepfake score
- explanation from the vision model
- recommended action

## Supported Image Types

The backend currently supports:

- JPEG / JPG
- PNG
- WebP
- GIF

This project is not limited to `.jpg`.

## Testing The Product

### Option 1: Test the backend directly

Use `curl` to verify the backend first:

```powershell
curl -X POST "http://127.0.0.1:8000/api/analyze-url" `
  -H "Content-Type: application/json" `
  -d "{\"image_url\":\"https://upload.wikimedia.org/wikipedia/commons/3/3f/Fronalpstock_big.jpg\"}"
```

If this returns JSON, the backend is working.

### Option 2: Test through the extension

1. Keep the backend running
2. Reload the extension if you changed any code
3. Visit a page with a normal visible image
4. Right-click the image
5. Run the analysis
6. Open the popup

### Recommended test cases

Test at least:

- a real photo
- an obviously AI-generated image
- an edited or suspicious image

## Important Notes About Real-World Websites

Not every site behaves the same way.

### Some sites block image downloads

Certain sites return `403 Forbidden` when the backend tries to download the image directly. This project includes a fallback path where the extension fetches the image in the browser and uploads it to the backend instead.

### Some sites do not expose a normal image element

The Chrome context menu item is configured for actual image elements. It may not appear or work reliably on:

- Google Images result thumbnails
- CSS background images
- canvas-rendered images
- custom gallery viewers
- some stock-photo and social media sites

For the best demo experience, start with plain article images or direct image URLs.

## Troubleshooting

### `403 Forbidden`

Cause:
- the website blocks direct server-side image fetches

What to do:
- retry after reloading the extension
- test on a simpler public image source
- use direct image URLs when possible

### `Analysis failed`

Check:

- is the backend running?
- are the API keys correct?
- is the internet connection active?
- is the backend URL in the popup correct?
- is the target a real image element?

### Right-click option does not appear

Cause:
- the clicked content is not a regular image element that Chrome recognizes for `contexts: ["image"]`

### Popup shows old state

Try:

- reload the extension in `chrome://extensions`
- rerun the analysis

## Security

- Store real secrets only in `backend/.env`
- Never commit `backend/.env`
- If keys are shared publicly by mistake, rotate them immediately

## Commands Summary

### Start backend

```powershell
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Install dependencies

```powershell
cd backend
.venv\Scripts\activate
pip install -r requirements.txt
```

### Reload the extension

1. Open `chrome://extensions`
2. Find the extension
3. Click `Reload`

## Hackathon Demo Summary

This project demonstrates a practical explainable-AI workflow for fake-content detection. The extension captures images directly from browsing activity, the backend orchestrates multiple analysis services, and the user receives a simple verdict with supporting explanation instead of an opaque score only.

## Future Improvements

- support background images and hovered elements with a content script
- save analysis history
- add screenshot-based analysis
- support batch checking
- improve verdict calibration with more signals

## License

Add a license before publishing publicly.
