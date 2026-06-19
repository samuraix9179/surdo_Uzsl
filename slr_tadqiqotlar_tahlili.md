# O'zbek Imo-Ishora Tili (UZSL) Loyihasi uchun SLR va SLT Tadqiqotlari Tahlili

Ushbu hujjatda so'nggi global Sign Language Recognition (SLR) va Sign Language Translation (SLT) tadqiqotlari hamda ularning UZSL loyihasiga qanday tatbiq qilinishi mumkinligi tahlil qilingan.

## 1. SignBERT va Pre-Trained Modellar
* **Tadqiqot:** SignBERT arxitekturasi skelet nuqtalarini (landmarks) katta hajmdagi belgisiz (unlabeled) videolar orqali oldindan o'rgatadi (pre-training) va keyin ma'lum bir ishora tili uchun kichik datasetlarda moslashtiradi (fine-tuning).
* **Loyihaga ta'siri:** Hozirda biz MediaPipe + LSTM/SL-GCN arxitekturasidan noldan o'rgatish orqali foydalanyapmiz. Agar SignBERT kabi pre-trained transformer modellarini olib, unga MediaPipe nuqtalarimizni uzatsak, model qo'llarning mayda harakatlarini ancha aniqroq taniydi. Bu "transfer learning" usuli orqali o'zbek surdo tilidagi nisbatan kichik datasetimiz bilan ham juda yuqori aniqlikka erishish imkonini beradi.

## 2. Gloss-Free Sign Language Translation (SLT)
* **Tadqiqot:** Odatdagi modellar ishorani alohida so'zga (gloss), keyin esa so'zlarni gapga o'giradi. So'nggi (Gloss-free SLT) tadqiqotlar ishorani oraliq so'zlarsiz to'g'ridan-to'g'ri tabiiy matnga (end-to-end) o'girishni taklif qilmoqda.
* **Loyihaga ta'siri:** Loyihamizdagi `grammar_translator.py` qismi hozirda har bir ishorani o'zbek tili grammatikasi (kelishiklar, ko'plik va boshqalar) bo'yicha birlashtiryapti. Gloss-free arxitektura qo'llanilsa, ushbu qoidali grammatik arxitekturani qisqartirish va yanada tabiiy gaplarga tarjima qilish imkoniyati yaratiladi.

## 3. LLM (Large Language Models) Integratsiyasi
* **Tadqiqot:** Katta til modellari (LLM - GPT-4, Llama va mahalliy modellar) ishora qilingan ayrim so'zlardan mantiqiy, to'liq jumlalar shakllantirishda post-processing sifatida ishlatilmoqda.
* **Loyihaga ta'siri:** Mobil ilova (Flutter) va telegram botimizda natijani chiqarishdan oldin, tarjima qilingan asosiy ishora so'zlarini lokal kichik LLM yoki API orqali qayta ishlasak, kar-soqov foydalanuvchilarning fikri 100% xatosiz va tushunarli o'zbek tiliga aylantiriladi.

## 4. Data Augmentation va 3D Avatar (GAN)
* **Tadqiqot:** Dataset kamligini qoplash uchun GAN (Generative Adversarial Networks) yoki 3D avatarlar yordamida sun'iy ishora videolari yaratiladi.
* **Loyihaga ta'siri:** Telegram bot orqali yig'ilgan videolarning yorug'ligi, orqa foni va tezligini sun'iy ravishda o'zgartirish orqali (augmentation), biz mavjud ma'lumotlarni o'nlab barobar ko'paytirishimiz mumkin. Bu ML modelimizni mobil ilova orqali real sharoitlarda ishlatganda (xiralik, turli burchaklar) chidamliroq qiladi.

## Xulosa va Takliflar
Eng tez va kutilgan natijani beradigan yechimlar:
1. Hozirgi uzsl_bot NLP mexanizmini Transformer asosidagi kichik SLT yoki LLM post-processing'ga ko'chirish.
2. ML modelining o'qitish jarayoniga `Data Augmentation` qo'shish (hamma kadrlar uchun avtomatik tarzda).
