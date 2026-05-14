from datetime import datetime
from zoneinfo import ZoneInfo

from config import ARABIC_MONTHS, TIMEZONE


def now_local() -> datetime:
    return datetime.now(ZoneInfo(TIMEZONE))


def fmt_dt_ar(dt: datetime) -> str:
    """تنسيق التاريخ بشكل جميل بالعربي بنظام 12 ساعة"""
    d = dt.astimezone(ZoneInfo(TIMEZONE))
    hour_12 = d.strftime("%I").lstrip("0") or "12"
    minute   = d.strftime("%M")
    period   = "صباحاً" if d.hour < 12 else "مساءً"
    return f"{d.day} {ARABIC_MONTHS[d.month]} {d.year} الساعة {hour_12}:{minute} {period}"


def build_reminder_label(remind_minutes: int) -> str:
    if remind_minutes == 0:
        return "بدون تذكير"
    if remind_minutes % 1440 == 0:
        days = remind_minutes // 1440
        return f"قبل {days} يوم" if days == 1 else f"قبل {days} أيام"
    if remind_minutes % 60 == 0:
        hours = remind_minutes // 60
        return f"قبل {hours} ساعة" if hours == 1 else f"قبل {hours} ساعات"
    return f"قبل {remind_minutes} دقيقة"


def time_until(event_dt: datetime) -> str:
    diff = event_dt - now_local()
    if diff.total_seconds() < 0:
        return "انتهى"
    days    = diff.days
    hours   = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60
    if days > 0:
        return f"بعد {days} يوم و{hours} ساعة"
    if hours > 0:
        return f"بعد {hours} ساعة و{minutes} دقيقة"
    return f"بعد {minutes} دقيقة"
