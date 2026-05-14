import calendar
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import ARABIC_MONTHS, TIMEZONE
from utils import now_local


# =========================
# القائمة الرئيسية
# =========================
def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ إضافة موعد", callback_data="menu_add")],
        [InlineKeyboardButton("📋 مواعيدي",     callback_data="menu_list")],
        [InlineKeyboardButton("❓ المساعدة",    callback_data="menu_help")],
    ])


# =========================
# التقويم
# =========================
def build_calendar(year: int, month: int) -> InlineKeyboardMarkup:
    keyboard = []

    # رأس الشهر مع أزرار التنقل
    keyboard.append([
        InlineKeyboardButton("◀️", callback_data=f"cal_prev_{year}_{month}"),
        InlineKeyboardButton(f"📅 {ARABIC_MONTHS[month]} {year}", callback_data="cal_ignore"),
        InlineKeyboardButton("▶️", callback_data=f"cal_next_{year}_{month}"),
    ])

    # أيام الأسبوع
    keyboard.append([
        InlineKeyboardButton(d, callback_data="cal_ignore")
        for d in ["أح", "اث", "ث", "أر", "خ", "ج", "س"]
    ])

    today = now_local()
    for week in calendar.monthcalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="cal_ignore"))
            else:
                day_dt = datetime(year, month, day, 23, 59, tzinfo=ZoneInfo(TIMEZONE))
                if day_dt < today:
                    row.append(InlineKeyboardButton(f"·{day}·", callback_data="cal_past"))
                else:
                    marker = "🔹" if (year == today.year and month == today.month and day == today.day) else ""
                    row.append(InlineKeyboardButton(f"{marker}{day}", callback_data=f"cal_day_{year}_{month}_{day}"))
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("❌ إلغاء", callback_data="conv_cancel")])
    return InlineKeyboardMarkup(keyboard)


# =========================
# اختيار الوقت
# =========================
def build_hour_keyboard() -> InlineKeyboardMarkup:
    am_hours = [(12, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5),
                (6, 6), (7, 7), (8, 8), (9, 9), (10, 10), (11, 11)]
    pm_hours = [(12, 12), (1, 13), (2, 14), (3, 15), (4, 16), (5, 17),
                (6, 18), (7, 19), (8, 20), (9, 21), (10, 22), (11, 23)]
    rows = []

    rows.append([InlineKeyboardButton("🌅 صباحاً (AM)", callback_data="cal_ignore")])
    for i in range(0, len(am_hours), 6):
        rows.append([
            InlineKeyboardButton(f"{display:02d}", callback_data=f"hour_{h24}")
            for display, h24 in am_hours[i:i+6]
        ])

    rows.append([InlineKeyboardButton("🌆 مساءً (PM)", callback_data="cal_ignore")])
    for i in range(0, len(pm_hours), 6):
        rows.append([
            InlineKeyboardButton(f"{display:02d}", callback_data=f"hour_{h24}")
            for display, h24 in pm_hours[i:i+6]
        ])

    rows.append([InlineKeyboardButton("❌ إلغاء", callback_data="conv_cancel")])
    return InlineKeyboardMarkup(rows)


def build_minute_keyboard() -> InlineKeyboardMarkup:
    minutes = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]
    rows = [
        [InlineKeyboardButton(f":{m:02d}", callback_data=f"min_{m}") for m in minutes[i:i+4]]
        for i in range(0, len(minutes), 4)
    ]
    rows.append([InlineKeyboardButton("❌ إلغاء", callback_data="conv_cancel")])
    return InlineKeyboardMarkup(rows)


# =========================
# اختيار التذكير
# =========================
def build_reminder_unit_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏱ دقائق", callback_data="rem_unit_minutes"),
            InlineKeyboardButton("🕐 ساعات", callback_data="rem_unit_hours"),
            InlineKeyboardButton("📆 أيام",  callback_data="rem_unit_days"),
        ],
        [InlineKeyboardButton("🔕 بدون تذكير", callback_data="rem_unit_none")],
        [InlineKeyboardButton("❌ إلغاء",      callback_data="conv_cancel")],
    ])


def build_reminder_amount_keyboard(unit: str) -> InlineKeyboardMarkup:
    options = {
        "minutes": (
            [5, 10, 15, 20, 30, 45, 60, 90, 120],
            ["5د", "10د", "15د", "20د", "30د", "45د", "ساعة", "1.5س", "2س"],
            1,
        ),
        "hours": (
            [1, 2, 3, 4, 6, 8, 12, 18, 24],
            ["1س", "2س", "3س", "4س", "6س", "8س", "12س", "18س", "يوم"],
            60,
        ),
        "days": (
            [1, 2, 3, 4, 5, 6, 7, 10, 14],
            ["1ي", "2ي", "3ي", "4ي", "5ي", "6ي", "أسبوع", "10ي", "أسبوعين"],
            1440,
        ),
    }
    amounts, labels, multiplier = options[unit]
    pairs = list(zip(amounts, labels))
    rows  = [
        [InlineKeyboardButton(lbl, callback_data=f"rem_val_{amt * multiplier}") for amt, lbl in pairs[i:i+3]]
        for i in range(0, len(pairs), 3)
    ]
    rows.append([InlineKeyboardButton("🔙 رجوع للوحدة", callback_data="rem_back_unit")])
    rows.append([InlineKeyboardButton("❌ إلغاء",        callback_data="conv_cancel")])
    return InlineKeyboardMarkup(rows)
