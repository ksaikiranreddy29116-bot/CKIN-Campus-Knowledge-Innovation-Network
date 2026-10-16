from src.database import get_db

def create_notification(recipient_id, message, notification_type="info", related_project_id=None, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    # Check if identical unread notification exists within last 5 minutes
    cursor.execute("""
        SELECT id FROM notifications
        WHERE recipient_id = ? AND message = ? AND is_read = 0
        AND created_at >= datetime('now', '-5 minutes')
    """, (recipient_id, message))
    if cursor.fetchone():
        conn.close()
        return
    cursor.execute(
        "INSERT INTO notifications (recipient_id, message, notification_type, related_project_id) VALUES (?, ?, ?, ?)",
        (recipient_id, message, notification_type, related_project_id)
    )
    conn.commit()
    conn.close()

def get_user_notifications(user_id, unread_only=False, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    if unread_only:
        cursor.execute("SELECT * FROM notifications WHERE recipient_id = ? AND is_read = 0 ORDER BY created_at DESC", (user_id,))
    else:
        cursor.execute("SELECT * FROM notifications WHERE recipient_id = ? ORDER BY created_at DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def mark_notification_read(notification_id, user_id, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = ? AND recipient_id = ?", (notification_id, user_id))
    conn.commit()
    conn.close()

def mark_all_notifications_read(user_id, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET is_read = 1 WHERE recipient_id = ?", (user_id,))
    conn.commit()
    conn.close()
