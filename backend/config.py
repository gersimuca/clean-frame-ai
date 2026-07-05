from pathlib import Path
from typing import Tuple

import torch
from pydantic_settings import BaseSettings


def resolve_device(requested: str) -> str:
    if requested == "cpu":
        return "cpu"
    if not torch.cuda.is_available():
        print("[!] CUDA not available. Using CPU.")
        return "cpu"
    try:
        torch.cuda.init()
        return "cuda"
    except RuntimeError as e:
        print(f"[!] CUDA init failed ({e}). Using CPU.")
        return "cpu"


class Settings(BaseSettings):
    db_path: Path = Path("./puralens.db")
    host: str = "0.0.0.0"
    port: int = 8000
    num_workers: int = 4
    device: str = resolve_device("cuda")
    batch_size: int = 32

    corrupt_enabled: bool = True
    min_image_size: int = 50
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
    framing_enabled: bool = True
    dog_confidence: float = 0.65
    min_box_ratio: float = 0.03
    max_box_ratio: float = 0.95
    require_dog_present: bool = True

    class Config:
        env_prefix = "PURALENS_"


settings = Settings()