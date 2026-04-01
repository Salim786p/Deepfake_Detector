from app.graph import build_detection_graph
from app.schemas import AnalysisResponse


class FakeContentDetectorAgent:
    def __init__(self) -> None:
        self._graph = build_detection_graph()

    async def analyze(
        self,
        *,
        source_image_url: str | None,
        source_page_url: str | None,
        image_sha256: str,
        image_width: int,
        image_height: int,
        sightengine_bytes: bytes,
        sightengine_mime_type: str,
        vision_bytes: bytes,
        vision_mime_type: str,
        huggingface_bytes: bytes,
        filename: str,
    ) -> AnalysisResponse:
        result = await self._graph.ainvoke(
            {
                "source_image_url": source_image_url,
                "source_page_url": source_page_url,
                "image_sha256": image_sha256,
                "image_width": image_width,
                "image_height": image_height,
                "sightengine_bytes": sightengine_bytes,
                "sightengine_mime_type": sightengine_mime_type,
                "vision_bytes": vision_bytes,
                "vision_mime_type": vision_mime_type,
                "huggingface_bytes": huggingface_bytes,
                "filename": filename,
            }
        )
        return result["analysis_response"]
