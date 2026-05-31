# UZSL TARJIMON — TEXNIK VAZIFA (TZ)

**Loyiha nomi:** UZSL Mobile Translator  
**Versiya:** 1.0 (MVP)  
**Sana:** 31.05.2026  
**Muallif:** Sam  
**Maqsad:** O'zbek imo-ishora tilini (UZSL) real vaqtda matn va ovozga tarjima qiluvchi mobil ilova yaratish  

---

## 1. UMUMIY MA'LUMOT

### 1.1 Loyihaning maqsadi
O'zbekistondagi kar va soqovlar uchun mobil ilova yaratish, bu ilova:
- Telefon kamerasi orqali imo-ishora tilini real vaqtda tanib oladi
- Tarjimani ekranda matn shaklida ko'rsatadi
- Matnni ovozli nutqqa aylantiradi (TTS)
- Bozor, avtobus, do'kon kabi kundalik muhitlarda foydalanish uchun mo'ljallangan

### 1.2 Maqsadli auditoriya
- **Birlamchi:** Kar va soqov foydalanuvchilar (O'zbekistonda ~30,000+ kishi)
- **Ikkilamchi:** Ularning oila a'zolari, do'stlari, savdo xodimlari, jamoat transporti xodimlari
- **Uchlamchi:** UZSL o'rganuvchi talabalar, surdo-tarjimonlar

### 1.3 Asosiy muammo
- O'zbekistonda professional surdo-tarjimonlar yetishmaydi
- Kar foydalanuvchilar oddiy kundalik vaziyatlarda (xarid, transport, tibbiy yordam) muloqotda qiynaladilar
- Bozorda UZSL uchun maxsus dastur mavjud emas

---

## 2. FUNKSIONAL TALABLAR

### 2.1 Asosiy funksiyalar (MVP — 1-bosqich)

* **F-1. Real vaqtli imo-ishora tanish**
  - Telefon old yoki orqa kamerasini yoqish
  - Foydalanuvchi qo'l harakatlarini real vaqtda kuzatish (minimum 15 FPS)
  - Yuz va og'iz mimikasini parallel ravishda kuzatish
  - Aniqlangan belgini ekranda ko'rsatish

* **F-2. Matn tarjimasi**
  - Imo-ishora ketma-ketligini to'liq o'zbek tiliga aylantirish
  - Grammatik to'g'rilash (UZSL grammatikasi o'zbek tilidan farq qiladi)
  - Ekranda katta, o'qish oson shriftda ko'rsatish

* **F-3. Ovozli chiqarish (TTS)**
  - O'zbek tilida tabiiy ovozli nutq
  - Tezlikni sozlash imkoniyati (sekin / o'rta / tez)
  - Erkak / ayol ovozi tanlash
  - Offline rejimda ham ishlash

* **F-4. Tarix va saqlash**
  - So'nggi tarjimalarni saqlash (oxirgi 100 ta)
  - Tez-tez ishlatiladigan iboralarni "Sevimlilar"ga qo'shish
  - Tarjimani matn yoki ovoz fayli sifatida eksport qilish

* **F-5. Foydalanuvchi interfeysi**
  - Sodda, katta tugmalar
  - Kontrast yuqori (ko'cha sharoiti uchun)
  - O'zbek va rus tillarida interfeys
  - Bir qo'l bilan ishlatish mumkin

### 2.2 Kengaytirilgan funksiyalar (2-bosqich)

* **F-6. Teskari tarjima**
  - Matn yoki ovoz kiritish → 3D avatar UZSL ko'rsatadi
  - Eshituvchi odam kar bilan muloqot qila olishi uchun

* **F-7. Lug'at rejimi**
  - UZSL alfaviti, raqamlar, asosiy iboralar
  - Video misollar bilan o'rganish moduli

* **F-8. Suhbat rejimi**
  - Ikki kishilik dialog (bir telefon, ikki tomon)
  - Real vaqtli ikki tomonlama tarjima

### 2.3 Kelajakdagi funksiyalar (3-bosqich)

- Bulutli sinxronizatsiya
- Kontekstli tarjima (joylashuvga qarab: bozor / shifoxona / bank)
- Foydalanuvchi shaxsiy lug'atini qo'shish
- Telegram bot integratsiyasi
- Smart watch (Apple Watch / Wear OS) qo'llab-quvvatlash

---

## 3. TEXNIK TALABLAR

### 3.1 Platformalar
- **Android:** 8.0 (API 26) va undan yuqori
- **iOS:** 13.0 va undan yuqori
- **Minimum RAM:** 3 GB
- **Bo'sh joy:** 200 MB (model bilan birga)

### 3.2 Texnologik stack

* **Frontend (Mobil ilova):**
  - **Framework:** Flutter 3.x
  - **Til:** Dart
  - **State management:** Riverpod yoki Bloc
  - **Kamera:** camera plugin (real-time stream)
  - **UI:** Material 3 + Cupertino

* **ML / Computer Vision (qurilmada — on-device):**
  - **MediaPipe Tasks API:** Holistic landmarker (yuz 468 + qo'l 21x2 + tana 33 = 543 ta nuqta)
  - **TensorFlow Lite:** Custom UZSL classifier model
  - **Model optimizatsiyasi:** Quantization (INT8), pruning

* **Backend (ixtiyoriy — 2-bosqich uchun):**
  - **Server:** Python (FastAPI) yoki Node.js
  - **Ma'lumotlar bazasi:** PostgreSQL + Redis (cache)
  - **Cloud:** AWS yoki Google Cloud Platform
  - **Storage:** S3 (video va model fayllari uchun)

* **Model trenirovkasi (ishlab chiqish):**
  - **Til:** Python 3.10+
  - **Framework:** PyTorch 2.x yoki TensorFlow 2.x
  - **Asosiy arxitektura:** Transformer + LSTM (sequence-to-sequence)
  - **Hardware:** NVIDIA GPU (minimum RTX 3060, ideal A100)

* **Ovoz (TTS):**
  - **Offline:** flutter_tts (o'zbek tilini qo'llab-quvvatlaydi)
  - **Online (sifatli):** Google Cloud TTS yoki Yandex SpeechKit

### 3.3 Arxitektura

```
┌─────────────────────────────────────────────────┐
│              MOBIL ILOVA (Flutter)              │
├─────────────────────────────────────────────────┤
│  UI Layer (Widgets, Screens)                    │
│  ├── Kamera ekrani                              │
│  ├── Tarjima ekrani                             │
│  └── Sozlamalar                                 │
├─────────────────────────────────────────────────┤
│  Business Logic (Riverpod / Bloc)               │
├─────────────────────────────────────────────────┤
│  ML Pipeline (on-device)                        │
│  ├── Kamera frame → MediaPipe Holistic          │
│  ├── 543 landmark → Buffer (30 frame window)    │
│  ├── TFLite model → UZSL belgi tasnifi          │
│  └── Post-processing → Matn + Ovoz              │
├─────────────────────────────────────────────────┤
│  Local Storage (SQLite + Hive)                  │
│  └── Tarix, sevimlilar, sozlamalar              │
└─────────────────────────────────────────────────┘
              ↕ (ixtiyoriy, 2-bosqich)
┌─────────────────────────────────────────────────┐
│        BACKEND (Cloud — kelajakda)              │
│  ├── Foydalanuvchi profili                      │
│  ├── Yangi model yangilanishlari (OTA)          │
│  └── Analitika va xatolar yig'ish               │
└─────────────────────────────────────────────────┘
```

### 3.4 ML Pipeline (batafsil)

1. **1-qadam: Kamera kiritish**
   - 30 FPS, 720p rezolyutsiyada video oqim
   - RGB formatda frame'larni olish

2. **2-qadam: Landmark ekstraksiyasi (MediaPipe Holistic)**
   - Har bir frame uchun:
     - 33 ta tana nuqtasi (pose)
     - 21 ta chap qo'l + 21 ta o'ng qo'l = 42 ta qo'l nuqtasi
     - 468 ta yuz nuqtasi (og'iz, qosh, ko'z ifodalari)
     - Jami: 543 ta (x, y, z) koordinata
   - Faqat shu raqamlar saqlanadi — video saqlanmaydi (maxfiylik)

3. **3-qadam: Sequence Buffer**
   - Oxirgi 30 frame (taxminan 1 soniya) landmark'larini buffer'ga olish
   - Sliding window yondashuvi

4. **4-qadam: Klassifikatsiya (TFLite)**
   - **Input:** 30 x 543 = 16,290 ta raqam
   - **Model:** Transformer encoder + classifier head
   - **Output:** UZSL belgisining ehtimolligi (softmax)
   - **Threshold:** 0.75 dan yuqori bo'lsa qabul qilinadi

5. **5-qadam: Post-processing**
   - Belgilar ketma-ketligini so'z va jumlaga aylantirish
   - Grammatik to'g'rilash (UZSL → O'zbek tili)
   - Yakuniy matn

6. **6-qadam: TTS**
   - Yakuniy matnni o'zbek tilida ovoz qilib chiqarish

### 3.5 Performance talablari

| Ko'rsatkich | Maqsadli qiymat |
| :--- | :--- |
| **FPS (real-time)** | ≥ 20 FPS |
| **Tanish kechikishi (latency)** | ≤ 500 ms |
| **Model aniqligi (top-1)** | ≥ 85% |
| **Model aniqligi (top-5)** | ≥ 95% |
| **Ilova hajmi** | ≤ 150 MB |
| **Model hajmi** | ≤ 30 MB |
| **Batareya iste'moli** | ≤ 8% / soat (faol foydalanish) |
| **Yuklash vaqti** | ≤ 3 soniya |

---

## 4. DATASET

### 4.1 Mavjud holat
- **UZSL uchun ochiq dataset YO'Q** — bu loyihaning eng katta muammosi.
- **Tegishli datasetlar:**
  - WLASL (American Sign Language) — 2,000 belgi
  - RSL (Russian Sign Language) — qisman kirish
  - INCLUDE (Indian Sign Language)

### 4.2 Dataset yig'ish strategiyasi

* **Bosqich 1 — MVP uchun (100 belgi):**
  - O'zbekistondagi karlar jamiyatlari bilan hamkorlik (masalan, "O'zbekiston Karlar Jamiyati")
  - 5-10 ta UZSL bo'yicha mutaxassis jalb qilish
  - Har bir belgi uchun 50-100 ta video (turli odamlar, sharoit, yorug'lik)
  - Jami: ~5,000–10,000 video

* **Bosqich 2 — Kengaytirish (500-1,000 belgi):**
  - Crowdsourcing platforma (foydalanuvchilar o'z videolarini yuborishi)
  - Universitetlardagi tilshunoslar bilan ishlash
  - Kasalxonalar, maktablarda video yozish

* **Bosqich 3 — To'liq tizim (5,000+ belgi):**
  - Doimiy yangilanish va yangi belgilar qo'shilishi

### 4.3 Birinchi 100 belgi (taklif)
Eng kerakli kundalik belgilar:
- **Salomlashish:** salom, xayr, rahmat, kechirasiz
- **Savollar:** nima, qancha, qayerda, qachon, qanday, kim
- **Raqamlar:** 0-100
- **Vaqt:** bugun, ertaga, kecha, hozir
- **Joylar:** uy, do'kon, bank, shifoxona, avtobus
- **Harakatlar:** bormoq, kelmoq, olmoq, bermoq, ko'rmoq
- **Tovarlar:** non, suv, sut, go'sht, sabzavot
- **Pul:** so'm, dollar, narx, qancha turadi
- **His-tuyg'ular:** yaxshi, yomon, og'rimoq, charchadim
- **Yordam:** yordam, kerak, tez yordam, politsiya

---

## 5. NOFUNKSIONAL TALABLAR

### 5.1 Maxfiylik va xavfsizlik
- **Video MAVJUD QURILMADAN CHIQMAYDI** — barcha ML qayta ishlash on-device (qurilmaning o'zida).
- Faqat landmark raqamlari (skeleton ma'lumotlari) saqlanishi mumkin.
- GDPR va O'zbekiston shaxsiy ma'lumotlar to'g'risidagi qonuniga muvofiqlik.
- Foydalanuvchi roziligi (consent) majburiy.

### 5.2 Foydalanuvchanlik (UX)
- Birinchi marta foydalanuvchi 3 daqiqada o'rganishi kerak.
- Onboarding bo'sh sahifalarsiz, intuitiv bo'lishi kerak.
- Imo-ishora ilovasini ishlatadigan odamlar uchun ovozli ko'rsatma o'rniga matn va video qo'llanma bo'lishi kerak.

### 5.3 Foydalanish qulayligi (Accessibility)
- VoiceOver / TalkBack to'liq qo'llab-quvvatlash.
- Yuqori kontrastli tema.
- Shrift hajmini sozlash.
- Rang ajrata olmaydigan (color blind) foydalanuvchilar uchun moslashish.

### 5.4 Tilga moslik
- **Interfeys:** O'zbek (lotin), O'zbek (kiril), Rus, Ingliz
- **Chiqish:** faqat O'zbek (MVP), keyinchalik Rus

### 5.5 Ishonchlilik
- Crash rate ≤ 0.5%
- Offline rejimda 100% asosiy funksiyalar ishlashi.
- Avtomatik xato hisoboti (foydalanuvchi roziligi bilan).

---

## 6. LOYIHA REJASI VA BOSQICHLARI

* **Bosqich 0 — Tadqiqot va tayyorlik (1-2 oy):**
  - Bozor tahlili, raqobatchilar.
  - UZSL mutaxassislari bilan suhbat.
  - Texnologik prototip (proof-of-concept).
  - Dataset yig'ish strategiyasi.

* **Bosqich 1 — MVP (3-5 oy):**
  - 50-100 ta belgini o'rgatish.
  - Flutter ilovasini yaratish.
  - MediaPipe + TFLite integratsiyasi.
  - Yopiq beta-test (20-50 foydalanuvchi).

* **Bosqich 2 — Ommaviy versiya (6-9 oy):**
  - 500+ belgiga kengaytirish.
  - Public release (Google Play + App Store).
  - Marketing va jamiyat ishi.
  - Foydalanuvchi fikrlarini yig'ish.

* **Bosqich 3 — Kengaytirish (10-12 oy):**
  - Teskari tarjima (matn → avatar).
  - Suhbat rejimi.
  - Backend integratsiyasi.
  - 1,000+ belgi.

---

## 7. JAMOA VA RESURSLAR

### 7.1 Minimal jamoa (MVP uchun)
- **Mobile dasturchi (Flutter):** 1 kishi (full-time)
- **ML muhandisi (Python, CV):** 1 kishi (full-time)
- **UI/UX dizayner:** 1 kishi (part-time)
- **UZSL mutaxassisi / konsultant:** 1-2 kishi (part-time)
- **Loyiha menejeri:** 1 kishi (part-time, bo'lishi mumkin Sam)

### 7.2 Texnik resurslar
- **Trenirovka uchun GPU:** Bulutli (Google Colab Pro, RunPod, Lambda Labs) — oyiga ~$200-500
- **Test qurilmalari:** 3-5 ta turli Android (eski va yangi) + 2 ta iOS
- **Backend (2-bosqich):** AWS / GCP — oyiga ~$100-300

### 7.3 Taxminiy byudjet (MVP, 5 oy)
- Maoshlar: $15,000-25,000
- Infratuzilma: $1,500-3,000
- Dataset yig'ish (mutaxassislar gonorari, video yozish): $3,000-5,000
- Marketing va beta-test: $1,000-2,000
- **JAMI: $20,500-35,000**
*(Eslatma: Agar siz o'zingiz dasturchi bo'lsangiz, byudjet sezilarli kamayadi.)*

---

## 8. XAVFLAR VA YENGISH

| Xavf | Ehtimollik | Ta'sir | Yengish strategiyasi |
| :--- | :--- | :--- | :--- |
| **Dataset yetishmasligi** | Yuqori | Kritik | Karlar jamiyati bilan erta hamkorlik, transfer learning |
| **Model aniqligi pastligi** | O'rta | Yuqori | Iterativ trenirovka, ko'proq ma'lumot, ensemble |
| **Mobil performance pastligi** | O'rta | Yuqori | Model quantization, GPU delegate, frame skipping |
| **Batareya tez quriydi** | Yuqori | O'rta | "Eco mode" rejimi, faqat tugma bosilganda yoqish |
| **Foydalanuvchilar qabul qilmasligi** | O'rta | Yuqori | Erta beta-test, jamiyat ishtiroki |
| **UZSL standartlashtirilmaganligi** | Yuqori | O'rta | Mintaqaviy variantlarni qo'llab-quvvatlash |
| **Raqobatchilar** | Past | O'rta | Tezroq bozorga chiqish, lokal afzallik |

---

## 9. MUVAFFAQIYAT MEZONLARI (KPI)

* **MVP bosqichi:**
  - ≥ 80% top-1 tanish aniqligi (100 belgi uchun)
  - ≥ 100 faol beta-test foydalanuvchisi
  - ≥ 4.0 / 5.0 foydalanuvchi reytingi
  - ≤ 500 ms tanish kechikishi

* **1 yil ichida:**
  - 10,000+ yuklab olish
  - 1,000+ kunlik faol foydalanuvchi (DAU)
  - 500+ UZSL belgisini qo'llab-quvvatlash
  - ≥ 90% tanish aniqligi

* **2 yil ichida:**
  - 50,000+ yuklab olish
  - O'zbekistondagi #1 surdo-yordam ilovasi
  - Davlat va xayriya tashkilotlari bilan rasmiy hamkorlik

---

## 10. KEYINGI QADAMLAR (DARHOL BAJARILADIGAN)

1. Bu hujjatni mutaxassislar bilan ko'rib chiqish — UZSL bo'yicha bilimdon kishi bilan.
2. O'zbekiston Karlar Jamiyati bilan bog'lanish — hamkorlik bo'yicha gaplashish.
3. **Texnik prototip yaratish (2 hafta):**
   - Flutter + MediaPipe Hands ulanishi.
   - 5-10 ta belgini sinov uchun yozib olish.
   - Eng oddiy klassifikator (k-NN yoki kichik MLP).
4. Jamoa to'plash — yuqorida ko'rsatilgan rollar uchun.
5. Byudjet va vaqt jadvalini aniqlashtirish.

---

## 11. ILOVALAR

### 11.1 Foydali manbalar
- MediaPipe Holistic: [developers.google.com/mediapipe](https://developers.google.com/mediapipe)
- Flutter: [flutter.dev](https://flutter.dev)
- TensorFlow Lite: [tensorflow.org/lite](https://www.tensorflow.org/lite)
- WLASL Dataset: [dxli94.github.io/WLASL/](https://dxli94.github.io/WLASL/)
- Sign Language Recognition tadqiqotlari: [arxiv.org](https://arxiv.org)

### 11.2 Aloqa
- **Loyiha rahbari:** Sam  
- **Joylashuv:** Tashkent, O'zbekiston  

---
*Hujjat oxiri. Bu Texnik Vazifa 1.0 versiyasi bo'lib, loyiha rivojlanishi bilan yangilanib boradi.*
