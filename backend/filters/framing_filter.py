import io
import torch
import torchvision
from torchvision import transforms
from PIL import Image


class FramingFilter:
    """Stage 3: Object detection for framing."""

    def __init__(self, device: str = "cuda"):
        self.device = device
        print("Loading Faster R-CNN for framing analysis...")

        weights = torchvision.models.detection.FasterRCNN_ResNet50_FPN_Weights.DEFAULT
        self.model = torchvision.models.detection.fasterrcnn_resnet50_fpn(weights=weights)

        try:
            self.model = self.model.to(self.device)
        except RuntimeError as e:
            err_msg = str(e).lower()
            if "nvidia driver" in err_msg or "cuda" in err_msg or "gpu" in err_msg:
                print(f"[!] GPU driver mismatch for Faster R-CNN. Falling back to CPU.")
                self.device = "cpu"
                self.model = self.model.to("cpu")
            else:
                raise

        self.model.eval()
        self.transform = transforms.Compose([transforms.ToTensor()])
        self.dog_label = 18

    @torch.no_grad()
    def check_bytes(self, image_bytes: bytes, confidence: float = 0.65, min_box_ratio: float = 0.03,
                    max_box_ratio: float = 0.95):
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as e:
            return False, 0.0, f"open_error_{e}", []

        img_tensor = self.transform(image).to(self.device)
        prediction = self.model([img_tensor])[0]

        boxes = prediction["boxes"].cpu().numpy()
        labels = prediction["labels"].cpu().numpy()
        scores = prediction["scores"].cpu().numpy()

        dog_mask = (labels == self.dog_label) & (scores >= confidence)
        dog_boxes = boxes[dog_mask]
        dog_scores = scores[dog_mask]

        detections = []
        for i, (box, score) in enumerate(zip(dog_boxes, dog_scores)):
            detections.append({
                "label": "dog",
                "confidence": float(score),
                "x1": float(box[0]),
                "y1": float(box[1]),
                "x2": float(box[2]),
                "y2": float(box[3]),
            })

        if len(dog_boxes) == 0:
            all_dog_scores = scores[labels == self.dog_label]
            best_attempt = float(all_dog_scores.max()) if len(all_dog_scores) > 0 else 0.0
            return False, round(best_attempt, 4), f"no_dog_detected(best_conf={best_attempt:.3f})", detections

        best_idx = int(dog_scores.argmax())
        x1, y1, x2, y2 = dog_boxes[best_idx]
        box_area = (x2 - x1) * (y2 - y1)
        img_area = image.width * image.height
        ratio = box_area / img_area

        if ratio < min_box_ratio:
            return False, round(ratio, 4), f"dog_too_small(ratio={ratio:.4f})", detections

        if ratio > max_box_ratio:
            return False, round(ratio, 4), f"dog_too_large(ratio={ratio:.4f},possible_fp)", detections

        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        norm_dist_x = abs(center_x - image.width / 2) / (image.width / 2)
        norm_dist_y = abs(center_y - image.height / 2) / (image.height / 2)
        center_score = 1.0 - (norm_dist_x + norm_dist_y) / 2

        composite_score = float(dog_scores[best_idx]) * (0.6 + 0.4 * center_score)
        return True, round(composite_score, 4), None, detections