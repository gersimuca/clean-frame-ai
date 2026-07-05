from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


class PipelineConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    input_dir: Optional[str] = Field(default=None, alias="inputDir")
    relevance_threshold: float = Field(default=0.30, alias="relevanceThreshold")
    dog_confidence: float = Field(default=0.65, alias="dogConfidence")
    min_box_ratio: float = Field(default=0.03, alias="minBoxRatio")
    max_box_ratio: float = Field(default=0.95, alias="maxBoxRatio")
    min_image_size: int = Field(default=50, alias="minImageSize")
    num_workers: int = Field(default=4, alias="numWorkers")
    device: str = Field(default="cuda", alias="device")
    corrupt_enabled: bool = Field(default=True, alias="corruptEnabled")
    relevance_enabled: bool = Field(default=True, alias="relevanceEnabled")
    framing_enabled: bool = Field(default=True, alias="framingEnabled")


class DetectionBox(BaseModel):
    label: str
    confidence: float
    x1: float
    y1: float
    x2: float
    x2: float
    y2: float


class ImageRecord(BaseModel):
    id: int
    filename: str
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