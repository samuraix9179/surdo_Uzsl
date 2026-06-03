import json
import os
import math

EXPORT_DIR = "exports"
LANDMARKS_DIR = os.path.join(EXPORT_DIR, "landmarks")
REPORT_PATH = os.path.join(EXPORT_DIR, "validation_report.json")


def is_all_zeros(flat_coords):
    """Koordinatalar ro'yxati faqat nollardan iboratligini tekshiradi."""
    return all(v == 0.0 for v in flat_coords)


def calculate_variance(sequence, hand_key):
    """Berilgan qo'l (left_hand/right_hand) nuqtalari uchun harakat variatsiyasini (variance) hisoblaydi.

    Juda past variatsiya (< 0.0001) qo'llarning deyarli harakatlanmaganini (statik) bildiradi.
    """
    trajectories = [frame[hand_key] for frame in sequence]
    if not trajectories or len(trajectories) < 2:
        return 0.0

    num_frames = len(trajectories)
    num_coords = len(trajectories[0])

    total_var = 0.0
    active_coords_count = 0

    for c in range(num_coords):
        values = [frame[c] for frame in trajectories]
        # Agar bu koordinata butun video davomida 0 bo'lgan bo'lsa (qo'l ko'rinmagan), hisobga olmaymiz
        if all(v == 0.0 for v in values):
            continue

        mean = sum(values) / num_frames
        variance = sum((v - mean) ** 2 for v in values) / num_frames
        total_var += variance
        active_coords_count += 1

    return total_var / active_coords_count if active_coords_count > 0 else 0.0


def validate_sample(json_path):
    """Bitta landmark JSON faylini chuqur tahlil va validate qiladi."""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"status": "CORRUPTED", "reason": f"Faylni o'qib bo'lmadi: {str(e)}"}

    metadata = data.get("metadata", {})
    frames_count = data.get("frames_count", 0)
    sequence = data.get("sequence", [])

    # 1. Struktura butunligi
    if frames_count != len(sequence):
        return {
            "status": "FAILED",
            "reason": f"Kadrlar soni mos kelmadi: frames_count={frames_count}, olingan={len(sequence)}"
        }

    if frames_count == 0:
        return {"status": "FAILED", "reason": "Videoda kadrlar topilmadi (bo'sh sequence)"}

    # 2. NaN yoki Inf qiymatlarni tekshirish
    for f_idx, frame in enumerate(sequence):
        for key in ["pose", "face", "left_hand", "right_hand"]:
            coords = frame.get(key, [])
            for c_val in coords:
                if math.isnan(c_val) or math.isinf(c_val):
                    return {"status": "FAILED", "reason": f"Kadr {f_idx} da cheksiz yoki NaN qiymat aniqlandi"}

    # 3. Hand Visibility Index (HVI) hisoblash
    left_hand_visible_frames = 0
    right_hand_visible_frames = 0
    at_least_one_hand_visible = 0

    for frame in sequence:
        lh_zeros = is_all_zeros(frame["left_hand"])
        rh_zeros = is_all_zeros(frame["right_hand"])

        if not lh_zeros:
            left_hand_visible_frames += 1
        if not rh_zeros:
            right_hand_visible_frames += 1
        if (not lh_zeros) or (not rh_zeros):
            at_least_one_hand_visible += 1

    lh_ratio = left_hand_visible_frames / frames_count
    rh_ratio = right_hand_visible_frames / frames_count
    any_hand_ratio = at_least_one_hand_visible / frames_count

    # 4. Motion Variance (Harakat variatsiyasi) hisoblash
    lh_var = calculate_variance(sequence, "left_hand")
    rh_var = calculate_variance(sequence, "right_hand")
    max_var = max(lh_var, rh_var)

    # 5. Qaror qabul qilish (Qoidalar)
    status = "PASSED"
    reasons = []

    # Qoida A: Imo-ishora qo'l bilan bajariladi, kamida bitta qo'l kadrlar 20% idan ko'pida ko'rinishi shart
    if any_hand_ratio < 0.20:
        status = "FAILED"
        reasons.append(f"Qo'llar juda kam ko'ringan (HVI = {any_hand_ratio:.1%})")

    # Qoida B: Harakat juda kam yoki statik (masalan volunteer harakatsiz turib qolgan)
    if status == "PASSED" and max_var < 0.0001 and any_hand_ratio > 0.0:
        status = "WARNING"
        reasons.append(f"Harakat o'ta sust yoki statik (Variance = {max_var:.6f})")

    return {
        "status": status,
        "frames_count": frames_count,
        "left_hand_hvi": lh_ratio,
        "right_hand_hvi": rh_ratio,
        "any_hand_hvi": any_hand_ratio,
        "left_hand_var": lh_var,
        "right_hand_var": rh_var,
        "max_variance": max_var,
        "reason": "; ".join(reasons) if reasons else "Sifat tekshiruvidan o'tdi",
        "metadata": metadata
    }


def main():
    meta_path = os.path.join(EXPORT_DIR, "metadata.json")
    if not os.path.exists(meta_path):
        print(f"[ERROR] '{meta_path}' topilmadi. Avval 'python -m utils.export' va nuqtalarni ajrating.")
        return

    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    print(f"[RUN] Starting validation of {len(metadata)} dataset landmark files...\n")

    report = {
        "summary": {
            "total_files": 0,
            "passed": 0,
            "failed": 0,
            "warning": 0,
            "average_frames": 0.0
        },
        "details": []
    }

    total_frames = 0

    for item in metadata:
        label = item["word_uz"]
        video_name = os.path.splitext(os.path.basename(item["path"]))[0]
        json_path = os.path.join(LANDMARKS_DIR, label, f"{video_name}.json")

        if not os.path.exists(json_path):
            print(f"[WARN] Landmark JSON topilmadi: {json_path}")
            continue

        res = validate_sample(json_path)
        res["file"] = os.path.relpath(json_path, EXPORT_DIR)
        report["details"].append(res)

        report["summary"]["total_files"] += 1
        total_frames += res.get("frames_count", 0)

        status = res["status"]
        if status == "PASSED":
            report["summary"]["passed"] += 1
            print(f"[PASS] {res['file']} | HVI: {res['any_hand_hvi']:.1%} | Var: {res['max_variance']:.5f}")
        elif status == "WARNING":
            report["summary"]["warning"] += 1
            print(f"[WARN] {res['file']} | {res['reason']}")
        else:
            report["summary"]["failed"] += 1
            print(f"[FAIL] {res['file']} | {res['reason']}")

    if report["summary"]["total_files"] > 0:
        report["summary"]["average_frames"] = total_frames / report["summary"]["total_files"]

    # Hisobotni JSON formatida yozish
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    sum_info = report["summary"]
    print("\n" + "="*50)
    print("DATASET VALIDATION SUMMARY REPORT")
    print("="*50)
    print(f"Jami tekshirilgan: {sum_info['total_files']} ta landmark JSON")
    print(f"Sifatli (Passed):  {sum_info['passed']}")
    print(f"Shubhali (Warning): {sum_info['warning']}")
    print(f"Yaroqsiz (Failed):  {sum_info['failed']}")
    print(f"O'rtacha kadrlar:  {sum_info['average_frames']:.1f} kadr/video")
    print("="*50)
    print(f"Batafsil hisobot saqlandi: {REPORT_PATH}\n")


if __name__ == "__main__":
    main()
