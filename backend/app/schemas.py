from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


VerdictLabel = Literal[
    "LIKELY_AUTHENTIC",
    "SUSPICIOUS",
    "LIKELY_AI_GENERATED",
    "LIKELY_DEEPFAKE",
]


class AnalyzeUrlRequest(BaseModel):
    image_url: HttpUrl
    page_url: Optional[HttpUrl] = None


class VisionAnalysis(BaseModel):
    provider: str
    model: str
    summary: str
    anomaly_score: float = Field(ge=0, le=1)
    manipulation_signals: List[str] = Field(default_factory=list)
    authenticity_cues: List[str] = Field(default_factory=list)
    explanation: str
    confidence_notes: str
    latency_ms: int


class ToolUsageMetadata(BaseModel):
    provider: str
    model: str
    latency_ms: int


class SightengineResult(BaseModel):
    ai_generated_score: float
    deepfake_score: float
    raw_response: Dict[str, Any]
    metadata: ToolUsageMetadata


class HuggingFaceDeepfakeResult(BaseModel):
    fake_score: float
    real_score: float
    predicted_label: str
    metadata: ToolUsageMetadata


class AnalysisResponse(BaseModel):
    verdict: VerdictLabel
    confidence: int = Field(ge=0, le=100)
    summary: str
    explanation: str
    recommended_action: str
    source_image_url: Optional[str] = None
    source_page_url: Optional[str] = None
    image_sha256: str
    image_width: int
    image_height: int
    sightengine: SightengineResult
    huggingface: HuggingFaceDeepfakeResult
    vision: VisionAnalysis
    completed_at: str


class HealthResponse(BaseModel):
    status: str
    app_name: str
