import time
from typing import Any, Dict

import httpx

from app.config import get_settings
from app.schemas import SightengineResult, ToolUsageMetadata


class SightengineError(RuntimeError):
    pass


async def analyze_with_sightengine(
    *,
    image_bytes: bytes,
    mime_type: str,
    filename: str,
) -> SightengineResult:
    settings = get_settings()
    started = time.perf_counter()

    data = {
        "models": "genai,deepfake",
        "api_user": settings.sightengine_user,
        "api_secret": settings.sightengine_secret,
    }
    files = {
        "media": (filename, image_bytes, mime_type),
    }

    timeout = httpx.Timeout(settings.request_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post("https://api.sightengine.com/1.0/check.json", data=data, files=files)
        response.raise_for_status()
        payload: Dict[str, Any] = response.json()

    if payload.get("status") != "success":
        raise SightengineError(payload.get("error", {}).get("message", "Sightengine analysis failed."))

    type_section = payload.get("type", {})
    ai_generated_score = float(type_section.get("ai_generated", 0.0) or 0.0)
    deepfake_score = float(type_section.get("deepfake", 0.0) or 0.0)

    elapsed_ms = round((time.perf_counter() - started) * 1000)
    return SightengineResult(
        ai_generated_score=ai_generated_score,
        deepfake_score=deepfake_score,
        raw_response=payload,
        metadata=ToolUsageMetadata(
            provider="Sightengine",
            model="genai,deepfake",
            latency_ms=elapsed_ms,
        ),
    )
