from datetime import date, datetime
from database import get_db_connection
import hashlib
import os

today = str(date.today())
SECRET_SALT = hashlib.sha256(f"{today}-{os.getenv('BASE_SECRET')}".encode()).hexdigest()

def save_message(message: str):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO chat_messages (message) VALUES (%s)",
            (message,)
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()

def save_visit(record: dict):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO visits (date, hour, path, referrer_domain, device, browser, visitor_hash)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (visitor_hash, date) DO NOTHING
            """,
            (
                record["date"], record["hour"], record["path"],
                record["referrer_domain"], record["device"],
                record["browser"], record["visitor_hash"],
            ),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()

def parse_device(ua: str) -> str:
    ua = ua.lower()
    if "mobile" in ua:
        return "mobile"
    elif "tablet" in ua:
        return "tablet"
    return "desktop"

def parse_browser(ua: str) -> str:
    ua = ua.lower()
    if "firefox" in ua:
        return "firefox"
    if "chrome" in ua:
        return "chrome"
    if "safari" in ua:
        return "safari"
    return "other"