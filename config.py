import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


@dataclass(frozen=True)
class S:
    # Faqat worker'da (emaktab.py — Selenium login) kerak. Bot bularni
    # ishlatmaydi, shuning uchun MAJBURIY emas — aks holda bot shu
    # o'zgaruvchilar yo'qligi sababli ishga tushmay qolardi.
    emaktab_login_url: str = os.getenv("EMAKTAB_LOGIN_URL", "")
    emaktab_home_url: str = os.getenv("EMAKTAB_HOME_URL", "")

    # Fayl yo'li YOKI FIREBASE_CREDENTIALS_JSON (pastda) — ikkalasidan
    # biri yetarli, shuning uchun bu ham MAJBURIY emas. Haqiqiy tekshiruv
    # firebase_client.py'da, Firestore'ga ulanilayotganda bo'ladi —
    # ikkalasi ham bo'sh bo'lsa, o'sha yerda tushunarli xato chiqadi.
    firebase_credentials: str = os.getenv("FIREBASE_CREDENTIALS", "")
    # Railway kabi joylarda fayl yuklab bo'lmaganda — butun JSON matnini
    # shu o'zgaruvchiga joylash mumkin (FIREBASE_CREDENTIALS o'rniga)
    firebase_credentials_json: str = os.getenv("FIREBASE_CREDENTIALS_JSON", "")

    # Bot HAM, worker HAM ishlatadi (parol/cookie shifrlash) — ikkalasida
    # ham bir xil bo'lishi SHART, shuning uchun bu haqiqatan majburiy.
    encryption_key: str = os.environ["EMAKTAB_ENC_KEY"]

    batch_size: int = int(os.getenv("SYNC_BATCH_SIZE", "40"))
    headless: bool = os.getenv("CHROME_HEADLESS", "true").lower() == "true"
    class_id: str = os.getenv("CLASS_ID", "9-A")
    # /api/sync-now va /api/cleanup-orphans uchun maxfiy token
    api_admin_token: str = os.getenv("API_ADMIN_TOKEN", "")
    # vergul bilan ajratilgan domenlar, masalan: https://maktab.netlify.app
    allowed_origins: str = os.getenv("ALLOWED_ORIGINS", "*")
    # eMaktab HTML'ini debug/ papkaga saqlash (shaxsiy ma'lumot bor!)
    debug_html: bool = os.getenv("EMAKTAB_DEBUG_HTML", "false").lower() == "true"


settings = S()
