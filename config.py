import os

# =========================
# إعدادات عامة
# =========================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")
TIMEZONE   = os.getenv("BOT_TIMEZONE", "Asia/Riyadh")
DB_PATH    = os.getenv("BOT_DB_PATH", "appointments.db")

ARABIC_MONTHS = [
    "", "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
    "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
]

# حالات المحادثة
TITLE, CAL_NAV, TIME_HOUR, TIME_MINUTE, REM_UNIT, REM_AMOUNT, CONFIRM_DELETE = range(7)
