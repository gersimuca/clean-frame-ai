import io
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel


class RelevanceFilter:
    """Stage 2: Zero-shot classification with CLIP."""

    def __init__(self, device: str = "cuda"):
        self.device = device
        print("Loading CLIP ViT-B/32 for relevance scoring...")

        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

        try:
            self.model = self.model.to(self.device)
        except RuntimeError as e:
            err_msg = str(e).lower()
            if "nvidia driver" in err_msg or "cuda" in err_msg or "gpu" in err_msg:
                print(f"[!] GPU driver mismatch for CLIP. Falling back to CPU.")
                self.device = "cpu"
                self.model = self.model.to("cpu")
            else:
                raise

        self.model.eval()

    @torch.no_grad()
    def check_bytes(self, image_bytes: bytes, dog_prompts, not_dog_prompts, threshold: float = 0.30):
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
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