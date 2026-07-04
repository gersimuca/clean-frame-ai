from pydantic_settings import BaseSettings
from typing import Tuple
from pathlib import Path


class Settings(BaseSettings):
    # Paths
    input_dir: Path = Path("./raw_dataset")
    output_dir: Path = Path("./cleaned_dataset")
    rejected_dir: Path = Path("./rejected_dataset")
    db_path: Path = Path("./puralens.db")
    static_dir: Path = Path("./static")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Processing
    num_workers: int = 4
    device: str = "cuda"
    batch_size: int = 32

    # Corrupt filter
    corrupt_enabled: bool = True
    min_image_size: int = 50

    # Relevance filter (CLIP zero-shot)
    relevance_enabled: bool = True
    relevance_threshold: float = 0.30
    dog_prompts: Tuple[str, ...] = (
        "a photo of a dog",
        "a photo of a puppy",
        "a photo of a canine",
        "a close-up photo of a dog",
    )
    not_dog_prompts: Tuple[str, ...] = (
        "a photo of a person",
        "a photo of a landscape",
        "a photo of text or document",
        "a photo of a building",
        "a photo of food",
        "a photo of a car",
        "a blurry photo",
    )

    # Framing filter (Object Detection)
    framing_enabled: bool = True
    dog_confidence: float = 0.65
    min_box_ratio: float = 0.03
    max_box_ratio: float = 0.95
    require_dog_present: bool = True

    class Config:
        env_prefix = "PURALENS_"


settings = Settings()