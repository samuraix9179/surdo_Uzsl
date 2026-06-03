import json
import os
import sys

try:
    import cv2
    import numpy as np
    import mediapipe as mp
except ImportError:
    print("⚠️ Ushbu skriptni ishlatish uchun quyidagi paketlarni o'rnating:")
    print("   pip install opencv-python mediapipe numpy")
    sys.exit(1)

EXPORT_DIR = "exports"
LANDMARKS_DIR = os.path.join(EXPORT_DIR, "landmarks")


def _get_coords(landmarks, num_points):
    """Landmarklardan x, y, z koordinatalarini flat list qilib oladi.

    Agar landmarklar yo'q bo'lsa (masalan qo'l ko'rinmasa), nollar bilan to'ldiradi.
    """
    if landmarks is None:
        return [0.0] * (num_points * 3)
    coords = []
    for lm in landmarks.landmark:
        coords.extend([lm.x, lm.y, lm.z])
    return coords


def process_video(video_path):
    """Bitta videoni o'qib, har bir kadr uchun 543 ta landmark (x, y, z) oladi."""
    mp_holistic = mp.solutions.holistic

    cap = cv2.VideoCapture(video_path)
    sequence = []

    # MediaPipe Holistic landmarker
    with mp_holistic.Holistic(
        static_image_mode=False,
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as holistic:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # MediaPipe RGB formatni talab qiladi
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image.flags.writeable = False

            # Landmarklarni aniqlash
            results = holistic.process(image)

            # Nuqtalarni flat listga aylantirish (x, y, z)
            # 1. Pose: 33 ta nuqta
            pose = _get_coords(results.pose_landmarks, 33)
            # 2. Face: 468 ta nuqta
            face = _get_coords(results.face_landmarks, 468)
            # 3. Chap qo'l: 21 ta nuqta
            left_hand = _get_coords(results.left_hand_landmarks, 21)
            # 4. O'ng qo'l: 21 ta nuqta
            right_hand = _get_coords(results.right_hand_landmarks, 21)

            # Jami: 543 ta nuqta -> 1629 ta koordinata qiymati
            frame_data = {
                "pose": pose,
                "face": face,
                "left_hand": left_hand,
                "right_hand": right_hand,
                "total_points": len(pose)//3 + len(face)//3 + len(left_hand)//3 + len(right_hand)//3
            }
            sequence.append(frame_data)

    cap.release()
    return sequence


def main():
    meta_path = os.path.join(EXPORT_DIR, "metadata.json")
    if not os.path.exists(meta_path):
        print(f"❌ '{meta_path}' topilmadi. Avval 'python -m utils.export' ni bajaring.")
        return

    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    os.makedirs(LANDMARKS_DIR, exist_ok=True)
    processed_count = 0

    print(f"🎬 {len(metadata)} ta videodan landmarklarni ajratish boshlandi...")

    for item in metadata:
        video_rel_path = item["path"]
        video_abs_path = os.path.join(EXPORT_DIR, video_rel_path)

        if not os.path.exists(video_abs_path):
            print(f"⚠️ Video fayli topilmadi: {video_abs_path}")
            continue

        label = item["word_uz"]
        label_dir = os.path.join(LANDMARKS_DIR, label)
        os.makedirs(label_dir, exist_ok=True)

        video_name = os.path.splitext(os.path.basename(video_abs_path))[0]
        json_output_path = os.path.join(label_dir, f"{video_name}.json")

        print(f"⏳ Processing: {video_rel_path} ...", end="", flush=True)

        # Landmarklarni kadrlar bo'yicha ajratamiz
        sequence = process_video(video_abs_path)

        # JSON formatda saqlaymiz
        payload = {
            "metadata": item,
            "frames_count": len(sequence),
            "sequence": sequence
        }

        with open(json_output_path, "w", encoding="utf-8") as out:
            json.dump(payload, out, ensure_ascii=False, indent=2)

        print(" ✅ Ajratildi")
        processed_count += 1

    print(f"\n🎉 Tugadi! Jami {processed_count} ta video muvaffaqiyatli qayta ishlandi.")
    print(f"📁 Landmark JSON fayllari saqlandi: {LANDMARKS_DIR}")


if __name__ == "__main__":
    main()
