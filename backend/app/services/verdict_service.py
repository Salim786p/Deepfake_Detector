from datetime import datetime, timezone

from app.schemas import AnalysisResponse, SightengineResult, VisionAnalysis


def _clamp_score(value: float) -> float:
    return max(0.0, min(1.0, value))


def _pick_recommended_action(verdict: str) -> str:
    if verdict == "LIKELY_DEEPFAKE":
        return "Treat this image as manipulated until independently verified."
    if verdict == "LIKELY_AI_GENERATED":
        return "Do not rely on this image as proof without external verification."
    if verdict == "SUSPICIOUS":
        return "Seek corroborating context, reverse-image search, and source verification."
    return "Low automated risk signal, but still verify source and surrounding context."


def merge_verdict(
    *,
    source_image_url: str | None,
    source_page_url: str | None,
    image_sha256: str,
    image_width: int,
    image_height: int,
    sightengine_result: SightengineResult,
    vision_result: VisionAnalysis,
) -> AnalysisResponse:
    ai_generated = _clamp_score(sightengine_result.ai_generated_score)
    deepfake = _clamp_score(sightengine_result.deepfake_score)
    strongest_signal = max(ai_generated, deepfake)

    if deepfake >= 0.75:
        verdict = "LIKELY_DEEPFAKE"
        confidence = round(deepfake * 100)
        summary = "Strong deepfake/manipulation signal detected."
    elif ai_generated >= 0.75:
        verdict = "LIKELY_AI_GENERATED"
        confidence = round(ai_generated * 100)
        summary = "Strong AI-generated image signal detected."
    elif strongest_signal >= 0.45:
        verdict = "SUSPICIOUS"
        confidence = round(strongest_signal * 100)
        summary = "The image shows moderate synthetic or manipulation risk signals."
    else:
        verdict = "LIKELY_AUTHENTIC"
        confidence = round((1.0 - strongest_signal) * 100)
        summary = "No strong synthetic or deepfake signal was detected."

    evidence_lines = [
        f"Sightengine scores: AI-generated {round(ai_generated * 100)}%, deepfake {round(deepfake * 100)}%.",
    ]

    if vision_result.manipulation_signals:
        evidence_lines.append(
            "Visual anomalies noted: " + "; ".join(vision_result.manipulation_signals[:3]) + "."
        )
    elif vision_result.authenticity_cues:
        evidence_lines.append(
            "Authenticity-supporting cues: " + "; ".join(vision_result.authenticity_cues[:3]) + "."
        )

    evidence_lines.append(
        f"{vision_result.provider} is used here for visual interpretation and explanation, not as the final authenticity detector."
    )

    explanation = " ".join(evidence_lines + [vision_result.explanation, vision_result.confidence_notes])

    return AnalysisResponse(
        verdict=verdict,
        confidence=confidence,
        summary=summary,
        explanation=explanation,
        recommended_action=_pick_recommended_action(verdict),
        source_image_url=source_image_url,
        source_page_url=source_page_url,
        image_sha256=image_sha256,
        image_width=image_width,
        image_height=image_height,
        sightengine=sightengine_result,
        vision=vision_result,
        completed_at=datetime.now(timezone.utc).isoformat(),
    )
