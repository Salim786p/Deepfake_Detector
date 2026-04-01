from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request

from app.agents.detector_agent import FakeContentDetectorAgent
from app.config import get_settings
from app.schemas import AnalysisResponse, AnalyzeUrlRequest, HealthResponse
from app.services.image_service import (
    ImagePreparationError,
    download_image_from_url,
    prepare_image,
)
from app.tools.gemini_vision_tool import GeminiVisionError
from app.tools.huggingface_detector_tool import HuggingFaceDeepfakeError
from app.tools.sightengine_tool import SightengineError


detector_agent = FakeContentDetectorAgent()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(
    title="Fake Content Detection Assistant API",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ImagePreparationError)
async def image_error_handler(_: Request, exc: ImagePreparationError):
    return _json_error(400, str(exc))


@app.exception_handler(GeminiVisionError)
async def gemini_error_handler(_: Request, exc: GeminiVisionError):
    return _json_error(502, f"Gemini Vision error: {exc}")


@app.exception_handler(HuggingFaceDeepfakeError)
async def huggingface_error_handler(_: Request, exc: HuggingFaceDeepfakeError):
    return _json_error(502, f"Hugging Face deepfake error: {exc}")


@app.exception_handler(SightengineError)
async def sightengine_error_handler(_: Request, exc: SightengineError):
    return _json_error(502, f"Sightengine error: {exc}")


def _json_error(status_code: int, detail: str):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=status_code, content={"detail": detail})


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok", app_name=settings.app_name)


@app.post("/api/analyze-url", response_model=AnalysisResponse)
async def analyze_url(payload: AnalyzeUrlRequest) -> AnalysisResponse:
    try:
        image_bytes, content_type, filename = await download_image_from_url(str(payload.image_url))
        prepared = prepare_image(
            image_bytes,
            content_type=content_type,
            filename=filename,
        )
        return await detector_agent.analyze(
            source_image_url=str(payload.image_url),
            source_page_url=str(payload.page_url) if payload.page_url else None,
            image_sha256=prepared.sha256,
            image_width=prepared.width,
            image_height=prepared.height,
            sightengine_bytes=prepared.original_bytes,
            sightengine_mime_type=prepared.original_mime_type,
            vision_bytes=prepared.analysis_bytes,
            vision_mime_type=prepared.analysis_mime_type,
            huggingface_bytes=prepared.analysis_bytes,
            filename=prepared.filename,
        )
    except (
        HTTPException,
        ImagePreparationError,
        GeminiVisionError,
        HuggingFaceDeepfakeError,
        SightengineError,
    ):
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {exc}") from exc


@app.post("/api/analyze-upload", response_model=AnalysisResponse)
async def analyze_upload(file: UploadFile = File(...)) -> AnalysisResponse:
    try:
        image_bytes = await file.read()
        prepared = prepare_image(
            image_bytes,
            content_type=file.content_type,
            filename=file.filename or "upload.jpg",
        )
        return await detector_agent.analyze(
            source_image_url=None,
            source_page_url=None,
            image_sha256=prepared.sha256,
            image_width=prepared.width,
            image_height=prepared.height,
            sightengine_bytes=prepared.original_bytes,
            sightengine_mime_type=prepared.original_mime_type,
            vision_bytes=prepared.analysis_bytes,
            vision_mime_type=prepared.analysis_mime_type,
            huggingface_bytes=prepared.analysis_bytes,
            filename=prepared.filename,
        )
    except (
        HTTPException,
        ImagePreparationError,
        GeminiVisionError,
        HuggingFaceDeepfakeError,
        SightengineError,
    ):
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {exc}") from exc
