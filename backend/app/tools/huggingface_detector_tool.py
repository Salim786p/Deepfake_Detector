import asyncio
import io
import time
from functools import lru_cache

import torch
from PIL import Image, ImageOps
from transformers import AutoImageProcessor, AutoModelForImageClassification

from app.config import get_settings
from app.schemas import HuggingFaceDeepfakeResult, ToolUsageMetadata


class HuggingFaceDeepfakeError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _load_model_bundle():
    settings = get_settings()
    model_id = settings.huggingface_deepfake_model
    processor = AutoImageProcessor.from_pretrained(model_id)
    model = AutoModelForImageClassification.from_pretrained(model_id)
    model.eval()
    return processor, model


def _resolve_label_indexes(model) -> tuple[int, int]:
    id2label = getattr(model.config, "id2label", {}) or {}
    fake_index = None
    real_index = None

    for index, label in id2label.items():
        normalized = str(label).strip().lower()
        if normalized in {"fake", "deepfake", "manipulated"} and fake_index is None:
            fake_index = int(index)
        if normalized in {"real", "authentic"} and real_index is None:
            real_index = int(index)

    if fake_index is None or real_index is None:
        raise HuggingFaceDeepfakeError("Unable to map fake/real labels for the Hugging Face model.")

    return fake_index, real_index


def _run_inference(image_bytes: bytes) -> HuggingFaceDeepfakeResult:
    settings = get_settings()
    started = time.perf_counter()

    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            processor, model = _load_model_bundle()
            fake_index, real_index = _resolve_label_indexes(model)
            inputs = processor(images=image, return_tensors="pt")
            with torch.no_grad():
                outputs = model(**inputs)
                probabilities = torch.nn.functional.softmax(outputs.logits, dim=1).squeeze(0)

            fake_score = float(probabilities[fake_index].item())
            real_score = float(probabilities[real_index].item())
    except HuggingFaceDeepfakeError:
        raise
    except Exception as exc:
        raise HuggingFaceDeepfakeError(
            "Hugging Face deepfake model inference failed. The model may still be downloading or incompatible."
        ) from exc

    elapsed_ms = round((time.perf_counter() - started) * 1000)
    predicted_label = "FAKE" if fake_score >= real_score else "REAL"
    return HuggingFaceDeepfakeResult(
        fake_score=max(0.0, min(1.0, fake_score)),
        real_score=max(0.0, min(1.0, real_score)),
        predicted_label=predicted_label,
        metadata=ToolUsageMetadata(
            provider="Hugging Face",
            model=settings.huggingface_deepfake_model,
            latency_ms=elapsed_ms,
        ),
    )


async def analyze_with_huggingface_deepfake(*, image_bytes: bytes) -> HuggingFaceDeepfakeResult:
    return await asyncio.to_thread(_run_inference, image_bytes)
