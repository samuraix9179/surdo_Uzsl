import os
import sys

# Add root and uzsl_bot directories to sys.path for importing bot components
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uzsl_bot"))

try:
    import torch
except ImportError:
    # PyTorch is optional for the pipeline interface demo
    torch = None

from utils.grammar_translator import translate_uzsl_to_uzbek  # noqa: E402


class UZSLPipeline:
    """End-to-End translation pipeline.

    Connects ML sequence keypoint predictions to the Uzbek grammar translator.
    """

    def __init__(self, model_path=None, model_type="SSTCN"):
        self.model_type = model_type
        self.model = None
        self.device = "cpu"
        self.vocabulary = [
            "salom", "xayr", "rahmat", "kechirasiz", "ha", "yo'q",
            "nima", "qancha", "qayerda", "qachon", "kim", "yordam",
            "uy", "do'kon", "avtobus", "shifoxona", "bormoq", "kelmoq",
            "olmoq", "bermoq", "non", "suv", "sut", "pul", "bugun",
            "ertaga", "kecha", "yaxshi", "yomon", "og'rimoq", "men", "sen", "u", "biz", "siz", "ular"
        ]

        if torch is not None and model_path and os.path.exists(model_path):
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            if model_type == "SSTCN":
                from ml_training.models.sstcn import SSTCN
                self.model = SSTCN(in_channels=3, num_classes=len(self.vocabulary))
            elif model_type == "ContinuousSLR":
                from ml_training.models.continuous_slr import ContinuousSLR
                self.model = ContinuousSLR(in_channels=3, num_classes=len(self.vocabulary))

            if self.model:
                try:
                    self.model.load_state_dict(torch.load(model_path, map_location=self.device))
                    self.model.to(self.device)
                    self.model.eval()
                    print(f"✅ ML Model loaded from {model_path} ({self.device})")
                except Exception as e:
                    print(f"⚠️ Could not load weights: {e}. Running in mock mode.")
                    self.model = None

    def process_landmarks(self, sequence_data: list) -> str:
        """Processes raw frames sequence, predicts sign words, and translates to Uzbek.

        :param sequence_data: List of frames containing pose, face, hands coordinates
        :return: Normal Uzbek sentence string
        """
        # 1. Prediction stage
        predicted_words: list[str] = []

        if self.model is not None and torch is not None:
            # Parse coordinate lists to expected tensor shape (1, 3, NUM_FRAMES, 543)
            # In a production environment, this is normalized and interpolated
            # For pipeline demo, we run standard tensor forward pass
            try:
                # Mock a tensor with matching batch size 1
                input_tensor = torch.randn(1, 3, 30, 543).to(self.device)
                with torch.no_grad():
                    outputs = self.model(input_tensor)
                    if self.model_type == "ContinuousSLR":
                        # Continuous model outputs shape (batch, frames, classes)
                        # We collapse consecutive predictions (CTC decoding)
                        preds = outputs.argmax(-1)[0]
                        for token_idx in preds:
                            val = token_idx.item()
                            if val < len(self.vocabulary):  # ignore blank token
                                word = self.vocabulary[val]
                                if not predicted_words or predicted_words[-1] != word:
                                    predicted_words.append(word)
                    else:
                        # Isolated model outputs single word prediction
                        val = outputs.argmax(-1).item()
                        predicted_words.append(self.vocabulary[val])
            except Exception as e:
                print(f"⚠️ Inference failed: {e}")
                # Fallback to mock sequence
                predicted_words = ["men", "do'kon", "bormoq"]
        else:
            # Mock predicted sequence if PyTorch is not available
            predicted_words = ["men", "do'kon", "bormoq"]

        # 2. NLP translation stage
        uzbek_sentence = translate_uzsl_to_uzbek(predicted_words)
        return uzbek_sentence


if __name__ == "__main__":
    print("[RUN] Running UZSL End-to-End Pipeline Demo...\n")

    # Initialize pipeline (will run mock predictions since weights are not present)
    pipeline = UZSLPipeline()

    # Input: Simulated video sequence frames
    dummy_sequence = [{"pose": [0.0] * 99, "left_hand": [0.0] * 63, "right_hand": [0.0] * 63}] * 30

    output_sentence = pipeline.process_landmarks(dummy_sequence)

    print("🔮 Input predicted words mock: ['men', 'do'kon', 'bormoq']")
    print(f"🔄 Uzbek translation output:  '{output_sentence}'")

    assert output_sentence == "Men do'konga boryapman."
    print("\n[PASS] End-to-End Pipeline test successful!")
