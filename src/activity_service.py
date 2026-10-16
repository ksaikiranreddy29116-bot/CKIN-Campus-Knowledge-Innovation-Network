from src.database import get_db

def log_activity(actor_id, action, entity_type, entity_id=None, details="", db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO activity_logs (actor_id, action, entity_type, entity_id, details) VALUES (?, ?, ?, ?, ?)",
        (actor_id, action, entity_type, entity_id, details)
    )
    conn.commit()
    conn.close()

def get_recent_activities(limit=50, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*, u.name as actor_name, u.role as actor_role
        FROM activity_logs a
        JOIN users u ON a.actor_id = u.id
        ORDER BY a.created_at DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
