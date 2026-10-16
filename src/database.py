import sqlite3
import os
from flask import g
from config import Config

def get_db_path(db_path=None):
    if db_path:
        return db_path
    return getattr(g, 'db_path', Config.DATABASE_PATH)

def get_db(db_path=None):
    if not db_path:
        try:
            from flask import current_app
            if current_app and current_app.config.get('DATABASE_PATH'):
                db_path = current_app.config['DATABASE_PATH']
        except Exception:
            pass
    target_path = db_path or Config.DATABASE_PATH
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path=None):
    target_path = db_path or Config.DATABASE_PATH
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    conn = get_db(target_path)
    cursor = conn.cursor()

    # Users Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('student', 'faculty', 'admin')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active INTEGER DEFAULT 1
    );
    ''')

    # Student Profiles Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS student_profiles (
        user_id INTEGER PRIMARY KEY,
        year INTEGER DEFAULT 1,
        cgpa REAL DEFAULT 0.0,
        skills TEXT DEFAULT '',
        interests TEXT DEFAULT '',
        preferred_project_type TEXT DEFAULT 'Web Application',
        availability_hours INTEGER DEFAULT 10,
        past_project_score REAL DEFAULT 75.0,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    ''')

    # Faculty Profiles Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS faculty_profiles (
        user_id INTEGER PRIMARY KEY,
        department TEXT DEFAULT 'Computer Science',
        expertise TEXT DEFAULT 'Artificial Intelligence, Software Engineering',
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    ''')

    # Projects Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        creator_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        domain TEXT NOT NULL,
        required_skills TEXT NOT NULL,
        difficulty_level TEXT DEFAULT 'Medium',
        project_type TEXT DEFAULT 'Web Application',
        weekly_commitment INTEGER DEFAULT 10,
        team_size INTEGER DEFAULT 4,
        expected_duration TEXT DEFAULT '3 Months',
        status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'completed')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (creator_id) REFERENCES users(id) ON DELETE CASCADE
    );
    ''')

    # Project Memberships Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS project_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        role_in_project TEXT DEFAULT 'Member',
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(project_id, student_id),
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
    );
    ''')

    # Join Requests Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS join_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        message TEXT DEFAULT '',
        status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'accepted', 'rejected')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(project_id, student_id),
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
    );
    ''')

    # Team Invitations Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS team_invitations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        inviter_id INTEGER NOT NULL,
        invitee_id INTEGER NOT NULL,
        status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'accepted', 'declined')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
        FOREIGN KEY (inviter_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (invitee_id) REFERENCES users(id) ON DELETE CASCADE
    );
    ''')

    # Project Tasks Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS project_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        assigned_to INTEGER,
        status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'in_progress', 'completed')),
        progress INTEGER DEFAULT 0 CHECK(progress >= 0 AND progress <= 100),
        due_date TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
        FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL
    );
    ''')

    # Notifications Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipient_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        notification_type TEXT DEFAULT 'info',
        related_project_id INTEGER,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (recipient_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (related_project_id) REFERENCES projects(id) ON DELETE CASCADE
    );
    ''')

    # Activity Logs Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actor_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id INTEGER,
        details TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE CASCADE
    );
    ''')

    # Recommendation History Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS recommendation_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        project_id INTEGER NOT NULL,
        compatibility_score REAL DEFAULT 0.0,
        ml_score REAL DEFAULT 0.0,
        similarity_score REAL DEFAULT 0.0,
        final_score REAL DEFAULT 0.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    );
    ''')

    # Project Comments Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS project_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        author_id INTEGER NOT NULL,
        comment_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
        FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE
    );
    ''')

    # Project Resources Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS project_resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        uploader_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        resource_url TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
        FOREIGN KEY (uploader_id) REFERENCES users(id) ON DELETE CASCADE
    );
    ''')

    # Project Milestones Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS project_milestones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        due_date TEXT DEFAULT '',
        status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'completed')),
        completed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    );
    ''')

    # Safe Schema Migrations for existing tables
    cursor.execute("PRAGMA table_info(projects)")
    proj_cols = [row[1] for row in cursor.fetchall()]
    if 'rejection_reason' not in proj_cols:
        cursor.execute("ALTER TABLE projects ADD COLUMN rejection_reason TEXT DEFAULT '';")
    if 'reviewer_id' not in proj_cols:
        cursor.execute("ALTER TABLE projects ADD COLUMN reviewer_id INTEGER;")
    if 'reviewed_at' not in proj_cols:
        cursor.execute("ALTER TABLE projects ADD COLUMN reviewed_at TIMESTAMP;")

    cursor.execute("PRAGMA table_info(project_tasks)")
    task_cols = [row[1] for row in cursor.fetchall()]
    if 'priority' not in task_cols:
        cursor.execute("ALTER TABLE project_tasks ADD COLUMN priority TEXT DEFAULT 'Medium';")

    conn.commit()
    conn.close()

