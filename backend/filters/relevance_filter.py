import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from pathlib import Path


class RelevanceFilter:
    """Zero-shot classification with CLIP."""

    def __init__(self, device: str = "cuda"):
        self.device = device
        print("Loading CLIP ViT-B/32...")
        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        self.model.eval()

    @torch.no_grad()
    def check(self, filepath: Path, dog_prompts, not_dog_prompts, threshold: float = 0.30):
        try:
            image = Image.open(filepath).convert("RGB")
        except Exception as e:
            return False, 0.0, f"open_error_{e}"

        texts = list(dog_prompts) + list(not_dog_prompts)
        inputs = self.processor(text=texts, images=image, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        outputs = self.model(**inputs)
        logits = outputs.logits_per_image[0]
        probs = logits.softmax(dim=0).cpu().numpy()

        n_pos = len(dog_prompts)
        pos_prob = float(probs[:n_pos].max())
        neg_prob = float(probs[n_pos:].max())
        margin = pos_prob - neg_prob

        if margin < threshold:
            return False, round(margin, 4), f"irrelevant(dog={pos_prob:.3f},other={neg_prob:.3f})"

        return True, round(margin, 4), None