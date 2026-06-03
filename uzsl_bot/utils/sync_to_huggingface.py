import os
import sys
from dotenv import load_dotenv

load_dotenv()

try:
    from huggingface_hub import HfApi, create_repo
except ImportError:
    print("⚠️ Ushbu sinxronizatsiya skriptini ishlatish uchun huggingface_hub-ni o'rnating:")
    print("   pip install huggingface_hub")
    sys.exit(1)

# Global tarmoq blokirovkalari (masalan, milliy firewalldan) o'tish uchun rasmiy oyna o'rnatiladi.
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# Sozlamalar (.env faylidan o'qiladi)
HF_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
HF_REPO = os.getenv("HUGGINGFACE_REPO", "samuraix9179/uzsl-dataset")
EXPORT_DIR = "exports"


def sync_dataset():
    """Yig'ilgan va ajratilgan UZSL landmarks va metadata fayllarini Hugging Face platformasiga sinxronizatsiya qiladi."""
    if not HF_TOKEN:
        print("❌ HUGGINGFACE_TOKEN topilmadi! .env faylida HUGGINGFACE_TOKEN-ni belgilang.")
        print("   Yordam: Hugging Face profilingiz sozlamalaridan 'Write' huquqi bilan Token oling.")
        return

    # Exports papkasi mavjudligini tekshirish
    if not os.path.exists(EXPORT_DIR):
        print(f"❌ '{EXPORT_DIR}' papkasi topilmadi. Avval landmarklarni eksport qiling!")
        return

    print("⚙️ Hugging Face platformasiga sinxronizatsiya boshlandi...")
    api = HfApi(token=HF_TOKEN)

    # 1. Repozitoriya mavjud bo'lmasa, uni yaratadi
    try:
        create_repo(
            repo_id=HF_REPO,
            token=HF_TOKEN,
            repo_type="dataset",
            private=True,  # Boshlang'ichda xavfsizlik uchun yopiq (private) qilamiz
            exist_ok=True
        )
        print(f"✅ Dataset repozitoriyasi tayyor: {HF_REPO}")
    except Exception as e:
        print(f"⚠️ Repozitoriya tekshirishda xato: {e}")

    # 2. Butun exports/landmarks va exports/metadata.json fayllarini yuklash
    try:
        print(f"⏳ Fayllar yuklanmoqda (yo'nalish: {EXPORT_DIR} ──► {HF_REPO}) ...")
        
        # Metadata.json ni alohida yuklaymiz
        meta_path = os.path.join(EXPORT_DIR, "metadata.json")
        if os.path.exists(meta_path):
            api.upload_file(
                path_or_fileobj=meta_path,
                path_in_repo="metadata.json",
                repo_id=HF_REPO,
                repo_type="dataset"
            )
            print("   └─ ✅ metadata.json yuklandi.")

        # Landmarklar papkasini to'liq yuklaymiz
        landmarks_path = os.path.join(EXPORT_DIR, "landmarks")
        if os.path.exists(landmarks_path):
            api.upload_folder(
                folder_path=landmarks_path,
                path_in_repo="landmarks",
                repo_id=HF_REPO,
                repo_type="dataset"
            )
            print("   └─ ✅ barcha landmark JSON fayllari yuklandi.")

        print(f"\n🎉 Muvaffaqiyatli yakunlandi! UZSL dataset Hugging Face-ga yuklandi.")
        print(f"🔗 Dataset havolasi: https://huggingface.co/datasets/{HF_REPO}")

    except Exception as e:
        print(f"\n❌ Yuklashda kutilmagan xatolik yuz berdi: {e}")


if __name__ == "__main__":
    sync_dataset()
