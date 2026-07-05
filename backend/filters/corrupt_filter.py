import io
from PIL import Image, ImageOps, UnidentifiedImageError
import cv2
import numpy as np


class CorruptFilter:
    """Stage 1: Detect unreadable, truncated, or malformed images."""

    def check_bytes(self, image_bytes: bytes, min_size: int = 50):
        if len(image_bytes) == 0:
            return False, 0.0, "empty_file"

        try:
            img = Image.open(io.BytesIO(image_bytes))
            img = ImageOps.exif_transpose(img)
            img.load()
            width, height = img.size

            if width < min_size or height < min_size:
                return False, 0.0, f"too_small_{width}x{height}"

            if width / height > 50 or height / width > 50:
                return False, 0.0, "extreme_aspect_ratio"

        except UnidentifiedImageError:
            return False, 0.0, "unidentified_image_format"
        except (OSError, SyntaxError) as e:
            return False, 0.0, f"decode_error_{type(e).__name__}"

        try:
            img_array = np.frombuffer(image_bytes, np.uint8)
            img_cv = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if img_cv is None:
                return False, 0.0, "opencv_decode_failed"
            if img_cv.shape[0] < min_size or img_cv.shape[1] < min_size:
                return False, 0.0, f"opencv_too_small_{img_cv.shape[1]}x{img_cv.shape[0]}"
        except Exception as e:
            return False, 0.0, f"opencv_exception_{e}"

        return True, 1.0, None