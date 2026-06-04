import os

try:
    from ultralytics import YOLO
except ImportError:
    print("⚠️ YOLOv8 modelini o'qitish uchun 'ultralytics' kutubxonasini o'rnating:")
    print("   pip install ultralytics")
    YOLO = None


def prepare_mock_yolo_dataset(base_dir="yolo_dataset"):
    """Prepares directory structure and mock images for YOLOv8 classification."""
    classes = ["A", "B", "C", "I", "O", "U"]
    splits = ["train", "val"]

    print(f"📁 Mock YOLO dataset yaratilmoqda: {base_dir}...")
    for split in splits:
        for cls in classes:
            path = os.path.join(base_dir, split, cls)
            os.makedirs(path, exist_ok=True)
            # Create a mock dummy text file acting as a mock image for pipeline test
            mock_img_path = os.path.join(path, "img_1.jpg")
            with open(mock_img_path, "w") as f:
                f.write("DUMMY IMAGE BYTES")


def train_yolo():
    print("⚙️ UZSL YOLOv8 Statik Daktil klassifikatsiyasini o'qitish boshlandi...")

    if YOLO is None:
        print("❌ YOLO topilmadi. O'qitish to'xtatildi.")
        return

    # 1. Prepare dataset path
    dataset_path = "yolo_dataset"
    if not os.path.exists(dataset_path):
        prepare_mock_yolo_dataset(dataset_path)

    # 2. Load pre-trained lightweight classification model
    print("🧬 Pretrained yolov8n-cls model yuklanmoqda...")
    model = YOLO("yolov8n-cls.pt")  # load pre-trained model

    # 3. Train classification model
    print("🔥 O'qitish jarayoni boshlanmoqda...")
    try:
        results = model.train(
            data=os.path.abspath(dataset_path),
            epochs=2,
            imgsz=224,
            batch=8,
            device="cpu"  # Force CPU for basic local execution check
        )
        print(f"🎉 O'qitish yakunlandi! Natijalar saqlandi: {results.save_dir}")
    except Exception as e:
        print(f"⚠️ O'qitish jarayonida xatolik: {e}")


if __name__ == "__main__":
    # If run directly and ultralytics is installed, run training
    if YOLO is not None:
        train_yolo()
    else:
        # Otherwise show mock preparation
        prepare_mock_yolo_dataset("yolo_dataset")
        print("\n[DONE] Mock YOLO dataset setup complete. Install 'ultralytics' to run training.")
