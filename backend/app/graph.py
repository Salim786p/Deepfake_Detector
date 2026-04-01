from typing import Any, Dict, TypedDict

from langgraph.graph import END, START, StateGraph

from app.schemas import AnalysisResponse, HuggingFaceDeepfakeResult, SightengineResult, VisionAnalysis
from app.services.verdict_service import merge_verdict
from app.tools.gemini_vision_tool import analyze_with_gemini_vision
from app.tools.huggingface_detector_tool import analyze_with_huggingface_deepfake
from app.tools.sightengine_tool import analyze_with_sightengine


class DetectionState(TypedDict, total=False):
    source_image_url: str | None
    source_page_url: str | None
    image_sha256: str
    image_width: int
    image_height: int
    sightengine_bytes: bytes
    sightengine_mime_type: str
    vision_bytes: bytes
    vision_mime_type: str
    huggingface_bytes: bytes
    filename: str
    sightengine_result: SightengineResult
    vision_result: VisionAnalysis
    huggingface_result: HuggingFaceDeepfakeResult
    analysis_response: AnalysisResponse


async def run_sightengine_node(state: DetectionState) -> Dict[str, Any]:
    result = await analyze_with_sightengine(
        image_bytes=state["sightengine_bytes"],
        mime_type=state["sightengine_mime_type"],
        filename=state["filename"],
    )
    return {"sightengine_result": result}


async def run_vision_node(state: DetectionState) -> Dict[str, Any]:
    result = await analyze_with_gemini_vision(
        image_bytes=state["vision_bytes"],
        mime_type=state["vision_mime_type"],
    )
    return {"vision_result": result}


async def run_huggingface_node(state: DetectionState) -> Dict[str, Any]:
    result = await analyze_with_huggingface_deepfake(
        image_bytes=state["huggingface_bytes"],
    )
    return {"huggingface_result": result}


def merge_verdict_node(state: DetectionState) -> Dict[str, Any]:
    response = merge_verdict(
        source_image_url=state.get("source_image_url"),
        source_page_url=state.get("source_page_url"),
        image_sha256=state["image_sha256"],
        image_width=state["image_width"],
        image_height=state["image_height"],
        sightengine_result=state["sightengine_result"],
        huggingface_result=state["huggingface_result"],
        vision_result=state["vision_result"],
    )
    return {"analysis_response": response}


def build_detection_graph():
    graph = StateGraph(DetectionState)
    graph.add_node("sightengine", run_sightengine_node)
    graph.add_node("vision", run_vision_node)
    graph.add_node("huggingface", run_huggingface_node)
    graph.add_node("merge_verdict", merge_verdict_node)

    graph.add_edge(START, "sightengine")
    graph.add_edge("sightengine", "vision")
    graph.add_edge("vision", "huggingface")
    graph.add_edge("huggingface", "merge_verdict")
    graph.add_edge("merge_verdict", END)

    return graph.compile()
