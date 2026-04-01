import base64
import json
import re
import time

import httpx

from app.config import get_settings
from app.schemas import VisionAnalysis


class GeminiVisionError(RuntimeError):
    pass


def _extract_json_block(text: str) -> dict:
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return json.loads(text)

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise GeminiVisionError("Gemini response did not contain valid JSON.")
    return json.loads(match.group(0))


async def analyze_with_gemini_vision(*, image_bytes: bytes, mime_type: str) -> VisionAnalysis:
    settings = get_settings()
    started = time.perf_counter()

    prompt = """
You are assisting a fake-content detection system.

Your job is NOT to decide whether the image is fake, AI-generated, or authentic.
Instead, provide a concise visual analysis that can help explain an authenticity verdict generated elsewhere.

Return strict JSON with this schema:
{
  "summary": "short one-sentence visual summary",
  "manipulation_signals": ["signal 1", "signal 2"],
  "authenticity_cues": ["cue 1", "cue 2"],
  "explanation": "2-4 sentence explanation focused on visible image cues only",
  "confidence_notes": "one sentence stating the limits of visual-only analysis"
}

Rules:
- Base your answer only on visible image characteristics.
- Do not identify people.
- Do not claim certainty about authenticity.
- If evidence is weak, say so.
- Return JSON only, with no markdown.
""".strip()

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64.b64encode(image_bytes).decode("utf-8"),
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
        },
    }

    timeout = httpx.Timeout(settings.request_timeout_seconds)
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
    )
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

    candidates = data.get("candidates", [])
    if not candidates:
        raise GeminiVisionError("Gemini did not return any candidates.")

    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts if part.get("text"))
    if not text:
        raise GeminiVisionError("Gemini did not return text output.")

    parsed = _extract_json_block(text)
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    confidence_notes = str(parsed.get("confidence_notes", "")).strip()
    if confidence_notes:
        confidence_notes = f"{confidence_notes} Gemini latency: {elapsed_ms} ms."
    else:
        confidence_notes = f"Visual-only interpretation has limits. Gemini latency: {elapsed_ms} ms."

    return VisionAnalysis(
        provider="Gemini",
        model=settings.gemini_model,
        summary=str(parsed.get("summary", "")).strip() or "Visual review completed.",
        manipulation_signals=[str(item).strip() for item in parsed.get("manipulation_signals", []) if str(item).strip()],
        authenticity_cues=[str(item).strip() for item in parsed.get("authenticity_cues", []) if str(item).strip()],
        explanation=str(parsed.get("explanation", "")).strip()
        or "Gemini reviewed the image for visible cues and generated an explanation.",
        confidence_notes=confidence_notes,
        latency_ms=elapsed_ms,
    )
