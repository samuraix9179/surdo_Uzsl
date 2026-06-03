# UZSL Mobile Translator — O'zbek Imo-Ishora Tili Tarjimoni

Ushbu loyiha O'zbek imo-ishora tilini (UZSL - Uzbek Sign Language) real vaqt rejimida matn va ovozli nutqqa tarjima qiluvchi mobil ilova (`uzsl_translator`) hamda dataset yig'ish tizimini (`uzsl_bot`) o'z ichiga oladi.

---

## 📂 Loyiha Tarkibi

Loyiha ikkita asosiy mustaqil komponentdan tashkil topgan:

1.  **`uzsl_translator` (Flutter Mobile App)**:
    *   **Native Android Bridge**: Google MediaPipe Holistic modelidan foydalanib, har bir kadr uchun 543 ta landmark nuqtalarini (yuz, tana, har ikki qo'l) real vaqtda 30 FPS tezlikda ajratib oladi.
    *   **Sliding Window Buffer**: Klassifikatorga uzatish uchun oxirgi 30 ta kadrning nuqtalar ketma-ketligini yig'ib boradi.
    *   **On-device ML**: Internet aloqasisiz (offline) imo-ishoralarni tanish imkoniyati.

2.  **`uzsl_bot` (Python Telegram Bot)**:
    *   **Kategoriyali Submission**: Imo-ishoralarni mavzular bo'yicha (`🤝 Salomlashish`, `❓ Savollar`, `🏠 Joylar` va hk) guruhlab, video yuborish chalkashliklarini yo'qotadi.
    *   **Erkin Tarjima (Custom Captions)**: Volunteerlar bazada mavjud bo'lmagan yangi so'zlarni ham yozib, video va video-notelar yubora oladilar.
    *   **Smart UZSL-to-Uzbek NLP**: Olmoshlar va kelishik qo'shimchalarini (`-ga`, `-da`, `-dan`) so'zlarning oxiriga qarab to'g'ri biriktirib, surdo so'zlar ketma-ketligini tabiiy o'zbek tiliga o'giruvchi aqlli mexanizm.
    *   **Sertifikat Generator**: Ko'ngillilar uchun o'zbek lotin va kirill yozuvlarini to'g'ri o'quvchi Unicode PDF sertifikat beruvchi ReportLab moduli.
    *   **Nuqtalar Ekstraktori**: Yig'ilgan videolardan MediaPipe Holistic orqali avtomatik ravishda neyron tarmoqqa tayyor JSON formatidagi datasetlarni ajratuvchi skript.

---

## 🏆 Mualliflar, Kengaytmalar va Ilhom Manbalari (Credits & Inspiration)

Ushbu loyihani rivojlantirishda global ochiq kodli hamjamiyatning (Open Source Community) Sign Language Recognition (SLR) mavzusidagi ilg'or yechimlari va tadqiqotlaridan ilhom olindi hamda foydalanildi. Mualliflik huquqlarini to'liq saqlagan holda quyidagi ochiq kodli loyihalar va ularning mualliflariga o'z minnatdorchiligimizni bildiramiz:

*   **Google MediaPipe & LSTM / Transformer Pipelines**:
    *   Skelet nuqtalarini real vaqtda aniqlash va neyron tarmoq modellari: [harshbg/Sign-Language-Interpreter-using-Deep-Learning](https://github.com/harshbg) hamda [jackyjsy/Gesture-Recognition](https://github.com/jackyjsy) loyihalaridan ilhomlanildi.
    *   CVPR 2021 SLR Challenge g'olibi bo'lgan **SAM-SLR (Skeleton-Aware Multi-modal SLR)** modeli, SL-GCN (Graph Convolutional Networks) va SSTCN (Separable Spatial-Temporal Convolution Network) arxitekturalari: [jackyjsy/CVPR21Chal-SLR](https://github.com/jackyjsy/CVPR21Chal-SLR) (CVPR 2021) loyihasi metodologiyalari qo'llanildi.
    *   1DCNN + Transformers yondashuvlari bo'yicha: `209sontung` va `Tachionstrahl` loyihalarining tadqiqot metodologiyalari qo'llanildi.
*   **YOLOv8 Statik Daktilologiya**:
    *   Statik barmoq harflari va daktillarni yuqori aniqlikda aniqlash: [MuhammadMoinFaisal/YOLOv8-Sign-Language-Detection](https://github.com/MuhammadMoinFaisal) loyihasi.
*   **Uzluksiz Imo-ishora Tarjimasi (Continuous SLR)**:
    *   GCN (Graph Convolutional Networks) va 3D CNN orqali to'liq gaplarni matnga o'girish: `0aqz0` loyihasining ochiq ilmiy ishlari.
*   **Telegram Mini App & WebApp**:
    *   React + TensorFlow.js orqali brauzer kamerasidan klijent tomonida real-time tarjima qilish: `MaheshNat` loyihasi.
*   **Gamification & Ta'lim Platformalari**:
    *   Imo-ishoralarni ko'rsatish orqali ballar yig'ish va surdo tilini interaktiv o'rgatish konsepsiyasi: `shubhammore1251` loyihasi.

Ushbu ochiq manbalar va mahalliy ko'ngillilar yordamida yig'iladigan **O'zbek Surdo Tili** datasetlari birlashib, O'zbekistondagi kar-soqov insonlar uchun muloqotni yengillashtiradigan mukammal #1 surdo-tarjimon mobil ilovasiga aylanadi.

---

## 🛠️ O'rnatish va Ishga tushirish yo'riqnomasi

Batafsil ma'lumotlar:
*   Mobil ilova uchun: [starter_kod.md](file:///d:/Loyihalar/surdo_uzsl/starter_kod.md) va [uzsl_translator/README.md](file:///d:/Loyihalar/surdo_uzsl/uzsl_translator/README.md)
*   Telegram bot va dataset yuklab olish uchun: [telegram_bot_tz.md](file:///d:/Loyihalar/surdo_uzsl/telegram_bot_tz.md) va [uzsl_bot/README.md](file:///d:/Loyihalar/surdo_uzsl/uzsl_bot/README.md)
