import logging

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN, CAL_NAV, TITLE, TIME_HOUR, TIME_MINUTE, REM_UNIT, REM_AMOUNT
from database import init_db
from handlers import (
    start, menu_handler, show_list,
    add_start, add_title, calendar_handler,
    time_hour_handler, time_minute_handler,
    reminder_unit_handler, reminder_amount_handler,
    delete_ask_handler, delete_confirm_handler,
    list_command, delete_command, cancel,
    reminder_job,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


def main() -> None:
    init_db()

    if not BOT_TOKEN or BOT_TOKEN == "PUT_YOUR_BOT_TOKEN_HERE":
        raise ValueError("8778898247:AAFexIa6S8lMOIU-MnK2HaZXj1wfw1s4iLY TELEGRAM_BOT_TOKEN")

    application = Application.builder().token(BOT_TOKEN).build()

    # ===== محادثة إضافة موعد =====
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("add", add_start),
            CallbackQueryHandler(add_start, pattern="^menu_add$"),
        ],
        states={
            TITLE:       [MessageHandler(filters.TEXT & ~filters.COMMAND, add_title)],
            CAL_NAV:     [CallbackQueryHandler(calendar_handler,       pattern="^cal_")],
            TIME_HOUR:   [CallbackQueryHandler(time_hour_handler,      pattern="^(hour_|conv_cancel)")],
            TIME_MINUTE: [CallbackQueryHandler(time_minute_handler,    pattern="^(min_|conv_cancel)")],
            REM_UNIT:    [CallbackQueryHandler(reminder_unit_handler,  pattern="^(rem_unit_|conv_cancel)")],
            REM_AMOUNT:  [CallbackQueryHandler(reminder_amount_handler,pattern="^(rem_val_|rem_back_unit|conv_cancel)")],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern="^conv_cancel$"),
        ],
    )

    # ===== تسجيل الهاندلرز =====
    application.add_handler(CommandHandler("start",  start))
    application.add_handler(CommandHandler("help",   start))
    application.add_handler(CommandHandler("list",   list_command))
    application.add_handler(CommandHandler("delete", delete_command))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(menu_handler,           pattern="^menu_"))
    application.add_handler(CallbackQueryHandler(delete_ask_handler,     pattern="^del_ask_"))
    application.add_handler(CallbackQueryHandler(delete_confirm_handler, pattern="^del_confirm_"))

    # ===== مهمة التذكير =====
    application.job_queue.run_repeating(reminder_job, interval=30, first=10)

    print("✅ البوت يعمل...")
    application.run_polling()


if __name__ == "__main__":
    main()
