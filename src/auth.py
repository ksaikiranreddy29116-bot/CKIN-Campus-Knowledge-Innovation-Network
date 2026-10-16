from werkzeug.security import generate_password_hash, check_password_hash
from src.database import get_db

def register_user(name, email, password, role='student', extra_data=None, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()

    email = email.strip().lower()
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        conn.close()
        return False, "Email already registered."

    hashed_password = generate_password_hash(password)
    try:
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (name, email, hashed_password, role)
        )
        user_id = cursor.lastrowid

        if role == 'student':
            extra = extra_data or {}
            cursor.execute(
                "INSERT INTO student_profiles (user_id, year, cgpa, skills, interests, preferred_project_type, availability_hours, past_project_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    user_id,
                    extra.get('year', 3),
                    extra.get('cgpa', 8.5),
                    extra.get('skills', 'Python, Flask, SQLite, Machine Learning'),
                    extra.get('interests', 'Artificial Intelligence, Web Development'),
                    extra.get('preferred_project_type', 'Web Application'),
                    extra.get('availability_hours', 15),
                    extra.get('past_project_score', 85.0)
                )
            )
        elif role == 'faculty':
            extra = extra_data or {}
            cursor.execute(
                "INSERT INTO faculty_profiles (user_id, department, expertise) VALUES (?, ?, ?)",
                (
                    user_id,
                    extra.get('department', 'Computer Science'),
                    extra.get('expertise', 'Artificial Intelligence, Software Engineering')
                )
            )

        conn.commit()
        conn.close()
        return True, user_id
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, str(e)

def authenticate_user(email, password, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    email = email.strip().lower()
    cursor.execute("SELECT id, name, email, password_hash, role, is_active FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return None, "Invalid email or password."
    
    if not user['is_active']:
        return None, "Account is disabled."

    if check_password_hash(user['password_hash'], password):
        return dict(user), "Authentication successful."
    else:
        return None, "Invalid email or password."

def get_user_by_id(user_id, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, role, created_at, is_active FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return None
    user_dict = dict(user)

    if user_dict['role'] == 'student':
        cursor.execute("SELECT * FROM student_profiles WHERE user_id = ?", (user_id,))
        profile = cursor.fetchone()
        if profile:
            user_dict['profile'] = dict(profile)
    elif user_dict['role'] == 'faculty':
        cursor.execute("SELECT * FROM faculty_profiles WHERE user_id = ?", (user_id,))
        profile = cursor.fetchone()
        if profile:
            user_dict['profile'] = dict(profile)

    conn.close()
    return user_dict
