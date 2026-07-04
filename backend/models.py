from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class PipelineConfig(BaseModel):
    input_dir: str
    output_dir: str = "./cleaned_dataset"
    rejected_dir: str = "./rejected_dataset"
    relevance_threshold: float = 0.30
    dog_confidence: float = 0.65
    min_box_ratio: float = 0.03
    max_box_ratio: float = 0.95
    min_image_size: int = 50
    num_workers: int = 4
    device: str = "cuda"
    corrupt_enabled: bool = True
    relevance_enabled: bool = True
    framing_enabled: bool = True


class DetectionBox(BaseModel):
    label: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float


class ImageRecord(BaseModel):
    id: int
    filename: str
    filepath: str
    status: str
    file_size_bytes: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    corrupt_pass: Optional[bool] = None
    corrupt_reason: Optional[str] = None
    relevance_score: Optional[float] = None
    relevance_reason: Optional[str] = None
    framing_score: Optional[float] = None
    framing_reason: Optional[str] = None
    detections: Optional[List[DetectionBox]] = None
    processed_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None


class ImageListResponse(BaseModel):
    images: List[ImageRecord]
    total: int


class StatsResponse(BaseModel):
    total: int
    pending: int
    accepted: int
    rejected: int
    error: int
    corrupt: int
    irrelevant: int
    bad_framing: int


class ProgressMessage(BaseModel):
    type: str
    progress: float
    stage: Optional[str] = None
    stats: Dict[str, int]
    message: Optional[str] = None
    level: str = "info"