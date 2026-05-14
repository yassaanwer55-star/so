import sqlite3
from datetime import datetime, timedelta

from config import DB_PATH
from utils import now_local


# =========================
# تهيئة قاعدة البيانات
# =========================
def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id         INTEGER NOT NULL,
            title           TEXT    NOT NULL,
            event_time      TEXT    NOT NULL,
            remind_minutes  INTEGER NOT NULL DEFAULT 0,
            sent_reminder   INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT    NOT NULL
        )
    """)
    # دعم الترقية من الإصدار القديم
    try:
        cur.execute("ALTER TABLE appointments ADD COLUMN remind_minutes INTEGER NOT NULL DEFAULT 0")
        cur.execute("ALTER TABLE appointments ADD COLUMN sent_reminder   INTEGER NOT NULL DEFAULT 0")
        cur.execute("UPDATE appointments SET remind_minutes = 1440 WHERE remind_1day = 1 AND remind_minutes = 0")
        cur.execute("UPDATE appointments SET remind_minutes = 60   WHERE remind_1hour = 1 AND remind_minutes = 0")
    except Exception:
        pass
    conn.commit()
    conn.close()


def _get_conn():
    return sqlite3.connect(DB_PATH)


# =========================
# عمليات CRUD
# =========================
def add_appointment(chat_id: int, title: str, event_time: datetime, remind_minutes: int) -> None:
    conn = _get_conn()
    conn.execute(
        "INSERT INTO appointments (chat_id, title, event_time, remind_minutes, created_at) VALUES (?,?,?,?,?)",
        (chat_id, title, event_time.isoformat(), int(remind_minutes), now_local().isoformat()),
    )
    conn.commit()
    conn.close()


def list_appointments(chat_id: int) -> list:
    conn = _get_conn()
    cur = conn.execute(
        """SELECT id, title, event_time, remind_minutes
           FROM appointments
           WHERE chat_id = ? AND event_time > ?
           ORDER BY event_time ASC""",
        (chat_id, now_local().isoformat()),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_appointment(chat_id: int, appointment_id: int):
    conn = _get_conn()
    cur = conn.execute(
        "SELECT id, title, event_time, remind_minutes FROM appointments WHERE chat_id = ? AND id = ?",
        (chat_id, appointment_id),
    )
    row = cur.fetchone()
    conn.close()
    return row


def delete_appointment(chat_id: int, appointment_id: int) -> bool:
    conn = _get_conn()
    cur = conn.execute(
        "DELETE FROM appointments WHERE chat_id = ? AND id = ?",
        (chat_id, appointment_id),
    )
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_pending_reminders(current_time: datetime) -> list:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, chat_id, title, event_time, remind_minutes, sent_reminder FROM appointments"
    ).fetchall()
    conn.close()

    due = []
    for appointment_id, chat_id, title, event_time_str, remind_minutes, sent_reminder in rows:
        if remind_minutes == 0 or sent_reminder:
            continue
        event_dt  = datetime.fromisoformat(event_time_str)
        remind_at = event_dt - timedelta(minutes=remind_minutes)
        if current_time >= remind_at:
            due.append((appointment_id, chat_id, title, event_dt, remind_minutes))
    return due


def mark_reminder_sent(appointment_id: int) -> None:
    conn = _get_conn()
    conn.execute("UPDATE appointments SET sent_reminder = 1 WHERE id = ?", (appointment_id,))
    conn.commit()
    conn.close()


def cleanup_old_appointments(current_time: datetime) -> None:
    threshold = (current_time - timedelta(days=2)).isoformat()
    conn = _get_conn()
    conn.execute("DELETE FROM appointments WHERE event_time < ?", (threshold,))
    conn.commit()
    conn.close()
