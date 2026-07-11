from pydantic import BaseModel, Field, ConfigDict


class PipelineConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

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


class StatsResponse(BaseModel):
    total: int
    pending: int
    accepted: int
    rejected: int
    error: int
    corrupt: int
    irrelevant: int
    badFraming: int
