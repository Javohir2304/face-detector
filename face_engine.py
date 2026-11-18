"""Yuzni aniqlash (YuNet) va tanish (SFace) — OpenCV modellari ustidagi yupqa qatlam."""
from pathlib import Path

import cv2
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
DETECTOR_MODEL = MODELS_DIR / "face_detection_yunet_2023mar.onnx"
RECOGNIZER_MODEL = MODELS_DIR / "face_recognition_sface_2021dec.onnx"

# SFace uchun OpenCV tavsiya qilgan cosine chegarasi: shundan past bo'lsa — boshqa odam.
MATCH_THRESHOLD = 0.363
# Shundan yuqori o'xshashlik 100% deb ko'rsatiladi.
FULL_MATCH = 0.75

cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)


def similarity_to_percent(similarity):
    """Cosine o'xshashlikni o'qish oson bo'lgan foizga aylantiradi.

    Bu ehtimollik emas, shkala: MATCH_THRESHOLD = 50%, FULL_MATCH va undan yuqori = 100%.
    """
    if similarity <= 0:
        return 0.0
    if similarity < MATCH_THRESHOLD:
        return 50.0 * similarity / MATCH_THRESHOLD
    return min(100.0, 50.0 + 50.0 * (similarity - MATCH_THRESHOLD) / (FULL_MATCH - MATCH_THRESHOLD))


def best_match(vector, names, matrix):
    """Bazadagi eng yaqin yuz: (ism, cosine o'xshashlik). Baza bo'sh bo'lsa (None, 0.0)."""
    if not names:
        return None, 0.0
    # Vektorlar normallashtirilgan, shuning uchun skalyar ko'paytma = cosine o'xshashlik.
    scores = matrix @ vector
    best = int(np.argmax(scores))
    return names[best], float(scores[best])


class FaceEngine:
    def __init__(self, score_threshold=0.8):
        for path in (DETECTOR_MODEL, RECOGNIZER_MODEL):
            if not path.exists():
                raise FileNotFoundError(f"Model topilmadi: {path} (README dagi yuklab olish buyrug'ini bajaring)")
        self.detector = cv2.FaceDetectorYN.create(str(DETECTOR_MODEL), "", (320, 320), score_threshold, 0.3, 5000)
        self.recognizer = cv2.FaceRecognizerSF.create(str(RECOGNIZER_MODEL), "")

    def detect(self, image):
        """Rasmdagi yuzlar: har biri [x, y, w, h, 5 ta nuqta (x, y)..., ishonch] — 15 ta son."""
        height, width = image.shape[:2]
        self.detector.setInputSize((width, height))
        _, faces = self.detector.detect(image)
        return [] if faces is None else list(faces)

    def embed(self, image, face):
        """Yuzning 128 o'lchamli, uzunligi 1 ga keltirilgan vektori."""
        aligned = self.recognizer.alignCrop(image, face)
        vector = self.recognizer.feature(aligned).flatten().astype(np.float32)
        return vector / np.linalg.norm(vector)

    def identify(self, image, names, matrix):
        """Rasmdagi har bir yuz: joyi, bazadagi eng yaqin odam, foiz va tanildimi."""
        results = []
        for face in self.detect(image):
            name, similarity = best_match(self.embed(image, face), names, matrix)
            results.append({
                "box": [int(v) for v in face[:4]],
                "name": name,
                "percent": round(similarity_to_percent(similarity), 1),
                "known": name is not None and similarity >= MATCH_THRESHOLD,
            })
        return results
