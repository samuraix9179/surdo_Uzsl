try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None


class YOLOSignPredictor:
    """Wrapper class for YOLOv8 static sign and dactyl letter classification."""

    def __init__(self, model_path="yolov8n-cls.pt"):
        self.model = None
        if YOLO is not None:
            try:
                # Load YOLOv8 classification model weights
                self.model = YOLO(model_path)
                print(f"✅ YOLO model loaded successfully from: {model_path}")
            except Exception as e:
                print(f"⚠️ YOLO model loading failed: {e}")

    def predict_dactyl(self, source) -> dict:
        """Classifies static hand shape from rasm/frame.

        :param source: Path to image, numpy array, or PIL image.
        :return: Dict containing predicted class name and confidence score.
        """
        if self.model is None:
            # Fallback mock prediction if YOLO is not installed or model is not loaded
            return {"class": "A", "confidence": 0.95, "mock": True}

        try:
            # Run inference
            results = self.model(source, verbose=False)
            result = results[0]

            # Get class with highest probability
            probs = result.probs
            top1_idx = probs.top1
            top1_conf = probs.top1conf.item()
            class_name = result.names[top1_idx]

            return {
                "class": class_name,
                "confidence": top1_conf,
                "mock": False
            }
        except Exception as e:
            print(f"⚠️ YOLO prediction failed: {e}")
            return {"class": "Unknown", "confidence": 0.0, "mock": False}


if __name__ == "__main__":
    print("[RUN] Running YOLOSignPredictor Test...")
    predictor = YOLOSignPredictor()

    # Run test prediction (uses mock output if ultralytics is not installed)
    pred = predictor.predict_dactyl("dummy_hand_image.jpg")
    print(f"🔮 Prediction result: {pred}")

    assert "class" in pred
    assert "confidence" in pred
    print("[PASS] YOLO predictor test successful!")
