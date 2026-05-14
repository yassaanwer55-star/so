import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from config import ARABIC_MONTHS, TIMEZONE, TITLE, CAL_NAV, TIME_HOUR, TIME_MINUTE, REM_UNIT, REM_AMOUNT
from database import (
    add_appointment, list_appointments, get_appointment,
    delete_appointment, get_pending_reminders, mark_reminder_sent, cleanup_old_appointments,
)
from keyboards import (
    main_menu_keyboard, build_calendar, build_hour_keyboard,
    build_minute_keyboard, build_reminder_unit_keyboard, build_reminder_amount_keyboard,
)
from utils import now_local, fmt_dt_ar, build_reminder_label, time_until

logger = logging.getLogger(__name__)


# =========================
# القائمة الرئيسية
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = "أهلاً 👋 أنا بوت المواعيد. كيف أقدر أساعدك؟"
    if update.message:
        await update.message.reply_text(text, reply_markup=main_menu_keyboard())
    else:
        await update.callback_query.edit_message_text(text, reply_markup=main_menu_keyboard())


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data  = query.data

    if data == "menu_add":
        await query.edit_message_text("✏️ أرسل اسم الموعد:")

    elif data == "menu_list":
        await show_list(query, context)

    elif data == "menu_help":
        await query.edit_message_text(
            "📖 *دليل الاستخدام*\n\n"
            "• اضغط *إضافة موعد* وأدخل الاسم، ثم اختر التاريخ والوقت من التقويم\n"
            "• في *مواعيدي* تقدر تشوف وتحذف مواعيدك مباشرة\n"
            "• يمكنك تحديد وقت التذكير بدقة: دقائق، ساعات، أو أيام قبل الموعد\n\n"
            "الأوامر السريعة:\n/add · /list · /delete",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")
            ]]),
        )

    elif data == "menu_back":
        await start(update, context)


async def show_list(query_or_update, context, edit: bool = True) -> None:
    """عرض قائمة المواعيد مع أزرار الحذف"""
    if hasattr(query_or_update, "message"):
        chat_id = query_or_update.message.chat_id
    else:
        chat_id = query_or_update.effective_chat.id

    appointments = list_appointments(chat_id)

    if not appointments:
        text   = "📭 ما عندك مواعيد قادمة."
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("➕ إضافة موعد", callback_data="menu_add")]])
    else:
        text    = "📋 *مواعيدك القادمة:*\n\n"
        buttons = []
        for aid, title, event_time_str, remind_mins in appointments:
            event_dt = datetime.fromisoformat(event_time_str)
            text += (
                f"*{title}*\n"
                f"🕐 {fmt_dt_ar(event_dt)}\n"
                f"⏳ {time_until(event_dt)}\n"
                f"🔔 {build_reminder_label(remind_mins)}\n\n"
            )
            buttons.append([InlineKeyboardButton(f"🗑 حذف: {title[:25]}", callback_data=f"del_ask_{aid}")])
        buttons.append([InlineKeyboardButton("➕ إضافة موعد", callback_data="menu_add")])
        markup = InlineKeyboardMarkup(buttons)

    if hasattr(query_or_update, "edit_message_text") and edit:
        await query_or_update.edit_message_text(text, parse_mode="Markdown", reply_markup=markup)
    elif hasattr(query_or_update, "message"):
        await query_or_update.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)


# =========================
# إضافة موعد – المحادثة
# =========================
async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    today = now_local()
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("✏️ أرسل اسم الموعد:")
    else:
        await update.message.reply_text("✏️ أرسل اسم الموعد:")
    return TITLE


async def add_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    title = update.message.text.strip()
    if len(title) > 100:
        await update.message.reply_text("⚠️ الاسم طويل جداً، اكتب أقل من 100 حرف.")
        return TITLE
    context.user_data["title"] = title
    today = now_local()
    await update.message.reply_text("📅 اختر تاريخ الموعد:", reply_markup=build_calendar(today.year, today.month))
    return CAL_NAV


async def calendar_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data  = query.data

    if data in ("cal_ignore", "cal_past"):
        return CAL_NAV

    if data == "conv_cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ تم الإلغاء.", reply_markup=main_menu_keyboard())
        return ConversationHandler.END

    if data.startswith(("cal_prev_", "cal_next_")):
        parts     = data.split("_")
        direction = parts[1]
        year, month = int(parts[2]), int(parts[3])
        if direction == "prev":
            month -= 1
            if month == 0:  month, year = 12, year - 1
        else:
            month += 1
            if month == 13: month, year = 1,  year + 1
        await query.edit_message_reply_markup(build_calendar(year, month))
        return CAL_NAV

    if data.startswith("cal_day_"):
        _, _, year, month, day = data.split("_")
        year, month, day = int(year), int(month), int(day)
        context.user_data.update(year=year, month=month, day=day)
        await query.edit_message_text(
            f"📅 التاريخ: {day} {ARABIC_MONTHS[month]} {year}\n\n🕐 اختر الساعة:",
            reply_markup=build_hour_keyboard(),
        )
        return TIME_HOUR

    return CAL_NAV


async def time_hour_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data  = query.data

    if data == "conv_cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ تم الإلغاء.", reply_markup=main_menu_keyboard())
        return ConversationHandler.END

    if data.startswith("hour_"):
        hour = int(data.split("_")[1])
        context.user_data["hour"] = hour
        y, m, d  = context.user_data["year"], context.user_data["month"], context.user_data["day"]
        h12      = hour % 12 or 12
        period   = "صباحاً" if hour < 12 else "مساءً"
        await query.edit_message_text(
            f"📅 التاريخ: {d} {ARABIC_MONTHS[m]} {y}\n🕐 الساعة: {h12:02d} {period}\n\n⏱ اختر الدقائق:",
            reply_markup=build_minute_keyboard(),
        )
        return TIME_MINUTE

    return TIME_HOUR


async def time_minute_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data  = query.data

    if data == "conv_cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ تم الإلغاء.", reply_markup=main_menu_keyboard())
        return ConversationHandler.END

    if data.startswith("min_"):
        minute = int(data.split("_")[1])
        y, m, d, h = (
            context.user_data["year"], context.user_data["month"],
            context.user_data["day"],  context.user_data["hour"],
        )
        dt = datetime(y, m, d, h, minute, tzinfo=ZoneInfo(TIMEZONE))

        if dt <= now_local():
            await query.edit_message_text("⚠️ هذا الوقت في الماضي! اختر وقتاً آخر.", reply_markup=build_hour_keyboard())
            return TIME_HOUR

        context.user_data["event_time"] = dt
        await query.edit_message_text(
            f"✅ *الموعد:* {context.user_data['title']}\n"
            f"📅 {fmt_dt_ar(dt)}\n"
            f"⏳ {time_until(dt)}\n\n"
            f"🔔 *اختر وحدة التذكير:*",
            parse_mode="Markdown",
            reply_markup=build_reminder_unit_keyboard(),
        )
        return REM_UNIT

    return TIME_MINUTE


async def reminder_unit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data  = query.data

    if data == "conv_cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ تم الإلغاء.", reply_markup=main_menu_keyboard())
        return ConversationHandler.END

    if data == "rem_unit_none":
        context.user_data["remind_minutes"] = 0
        return await _save_appointment(query, context)

    if data.startswith("rem_unit_"):
        unit    = data.replace("rem_unit_", "")
        unit_ar = {"minutes": "الدقائق", "hours": "الساعات", "days": "الأيام"}[unit]
        context.user_data["rem_unit"] = unit
        dt = context.user_data["event_time"]
        await query.edit_message_text(
            f"✅ *الموعد:* {context.user_data['title']}\n"
            f"📅 {fmt_dt_ar(dt)}\n\n"
            f"🔔 كم {unit_ar} قبل الموعد تريد التذكير؟",
            parse_mode="Markdown",
            reply_markup=build_reminder_amount_keyboard(unit),
        )
        return REM_AMOUNT

    return REM_UNIT


async def reminder_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data  = query.data

    if data == "conv_cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ تم الإلغاء.", reply_markup=main_menu_keyboard())
        return ConversationHandler.END

    if data == "rem_back_unit":
        dt = context.user_data["event_time"]
        await query.edit_message_text(
            f"✅ *الموعد:* {context.user_data['title']}\n"
            f"📅 {fmt_dt_ar(dt)}\n\n"
            f"🔔 *اختر وحدة التذكير:*",
            parse_mode="Markdown",
            reply_markup=build_reminder_unit_keyboard(),
        )
        return REM_UNIT

    if data.startswith("rem_val_"):
        remind_minutes = int(data.replace("rem_val_", ""))
        dt         = context.user_data["event_time"]
        remind_at  = dt - timedelta(minutes=remind_minutes)
        if remind_at <= now_local():
            await query.answer("⚠️ وقت التذكير هذا قد مضى! اختر فترة أقصر.", show_alert=True)
            return REM_AMOUNT
        context.user_data["remind_minutes"] = remind_minutes
        return await _save_appointment(query, context)

    return REM_AMOUNT


async def _save_appointment(query, context) -> int:
    title          = context.user_data["title"]
    event_time     = context.user_data["event_time"]
    remind_minutes = context.user_data.get("remind_minutes", 0)
    chat_id        = query.message.chat_id

    add_appointment(chat_id, title, event_time, remind_minutes)

    await query.edit_message_text(
        f"✅ *تم حفظ الموعد!*\n\n"
        f"📌 {title}\n"
        f"📅 {fmt_dt_ar(event_time)}\n"
        f"⏳ {time_until(event_time)}\n"
        f"🔔 {build_reminder_label(remind_minutes)}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 عرض كل المواعيد", callback_data="menu_list")],
            [InlineKeyboardButton("➕ إضافة موعد آخر",  callback_data="menu_add")],
        ]),
    )
    context.user_data.clear()
    return ConversationHandler.END


# =========================
# حذف موعد
# =========================
async def delete_ask_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    appointment_id = int(query.data.split("_")[2])
    chat_id        = query.message.chat_id

    row = get_appointment(chat_id, appointment_id)
    if not row:
        await query.answer("⚠️ الموعد غير موجود!", show_alert=True)
        return

    aid, title, event_time_str, _ = row
    event_dt = datetime.fromisoformat(event_time_str)

    await query.edit_message_text(
        f"🗑 *هل تريد حذف هذا الموعد؟*\n\n📌 {title}\n📅 {fmt_dt_ar(event_dt)}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ نعم، احذف", callback_data=f"del_confirm_{aid}"),
            InlineKeyboardButton("❌ لا، رجوع",  callback_data="menu_list"),
        ]]),
    )


async def delete_confirm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query          = update.callback_query
    await query.answer()
    appointment_id = int(query.data.split("_")[2])
    chat_id        = query.message.chat_id

    if delete_appointment(chat_id, appointment_id):
        await query.answer("✅ تم الحذف!", show_alert=False)
    else:
        await query.answer("⚠️ حدث خطأ.", show_alert=True)
    await show_list(query, context)


# =========================
# أوامر نصية (اختصارات)
# =========================
async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await show_list(update, context, edit=False)


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.args:
        try:
            aid     = int(context.args[0])
            deleted = delete_appointment(update.effective_chat.id, aid)
            msg     = "✅ تم حذف الموعد." if deleted else "⚠️ ما لقيت موعد بهذا الرقم."
            await update.message.reply_text(msg)
        except ValueError:
            await update.message.reply_text("اكتب رقم الموعد. مثال: /delete 3")
    else:
        await show_list(update, context, edit=False)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("❌ تم الإلغاء.", reply_markup=main_menu_keyboard())
    return ConversationHandler.END


# =========================
# مهمة التذكير التلقائي
# =========================
async def reminder_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    current_time   = now_local()
    due_reminders  = get_pending_reminders(current_time)

    for appointment_id, chat_id, title, event_dt, remind_minutes in due_reminders:
        message = (
            f"⏰ *تذكير بموعدك*\n\n"
            f"📌 {title}\n"
            f"📅 {fmt_dt_ar(event_dt)}\n"
            f"⏳ {time_until(event_dt)}\n"
            f"🔔 {build_reminder_label(remind_minutes)}"
        )
        try:
            await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
            mark_reminder_sent(appointment_id)
        except Exception as exc:
            logger.exception("Failed to send reminder: %s", exc)

    cleanup_old_appointments(current_time)
