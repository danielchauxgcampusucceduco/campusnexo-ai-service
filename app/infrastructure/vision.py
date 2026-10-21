"""YOLO inference: frames are decoded and discarded in memory; response contains counts only."""
import os

class VisionUnavailable(RuntimeError): pass

class YoloCounter:
    def __init__(self):
        self.model = None
        self.model_path = os.getenv("YOLO_MODEL", "yolo26n.pt")

    def _load(self):
        if self.model is None:
            try:
                from ultralytics import YOLO
                self.model = YOLO(self.model_path)
            except Exception as exc:
                raise VisionUnavailable("YOLO no disponible. Instala el extra [vision] y configura los pesos.") from exc
        return self.model

    def count_people(self, image_bytes: bytes) -> dict:
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            raise VisionUnavailable("OpenCV no está instalado. Instala el extra [vision].") from exc
        array = np.frombuffer(image_bytes, dtype=np.uint8)
        frame = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("No se pudo decodificar la imagen")
        result = self._load().predict(source=frame, verbose=False)[0]
        count = sum(1 for cls in result.boxes.cls.tolist() if int(cls) == 0) if result.boxes is not None else 0
        # No se serializa la imagen, bounding boxes, identidades ni embeddings.
        del frame, array, result
        return {"people_count": count,
                "privacy": "frame_discarded_in_process", "model": os.path.basename(self.model_path)}
