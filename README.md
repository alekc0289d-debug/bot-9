# Maktab Telegram bot (aiogram v3)

Bu faqat bot qismi — eMaktab worker BU YERDA YO'Q, alohida zipda
(`worker.zip`). Ikkalasi ham bitta Firebase bazasiga ulanadi, shuning
uchun `.env` dagi `FIREBASE_CREDENTIALS` va ayniqsa `EMAKTAB_ENC_KEY`
worker bilan **bir xil** bo'lishi shart (parol/cookie shifrlash kaliti).

## O'rnatish

    pip install -r requirements.txt
    cp .env.example .env   # to'ldiring

## Ishga tushirish

    python run_bot.py

## Railway'ga joylash

1. Bu papkani (worker bilan aralashtirmasdan) alohida GitHub repo qiling
   va push qiling.
2. Railway → New Project → Deploy from GitHub repo.
3. Railway avtomatik `requirements.txt` ni topib, `python run_bot.py`
   bilan ishga tushirishga harakat qiladi (Nixpacks). Agar tushirmasa,
   Settings → Deploy → **Custom Start Command**: `python run_bot.py`.
4. Variables bo'limiga `.env.example` dagi hamma o'zgaruvchini kiriting.
5. `firebase-service-account.json` faylini repo bilan yubormang (git'ga
   qo'shilmaydi) — Railway'da **Variables → Raw Editor** orqali butun
   JSON matnini `FIREBASE_CREDENTIALS_JSON` nomli o'zgaruvchiga joylab,
   ishga tushishdan oldin faylga yozib oluvchi kichik kodni
   `run_bot.py` boshiga qo'shishingiz kerak bo'ladi — buni xohlasangiz
   men yozib beraman (Railway'da doim shunday qilinadi, chunki fayl
   yuklab bo'lmaydi, faqat matn o'zgaruvchi).

Diqqat: Railway'ning bepul sinovi (~$5 kredit) 30 kunda tugaydi, shundan
keyin to'lov usuli qo'shish yoki Hobby ($5/oy) rejasiga o'tish kerak
bo'ladi.
