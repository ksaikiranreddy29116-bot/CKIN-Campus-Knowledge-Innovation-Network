from src.database import init_db, get_db
from src.auth import register_user, authenticate_user
from src.project_service import create_project, approve_project, create_project_task

def seed_data(db_path=None):
    print("Initializing Database structure...")
    init_db(db_path)

    print("Seeding Demo Users...")
    # Demo Student
    s_success, s_id = register_user(
        name="Alex Rivera",
        email="student@ckin.local",
        password="password123",
        role="student",
        extra_data={
            "year": 3,
            "cgpa": 8.8,
            "skills": "Python, Flask, SQLite, Machine Learning, Scikit-Learn, HTML/CSS",
            "interests": "Artificial Intelligence, Data Science, Web Application",
            "preferred_project_type": "Web Application",
            "availability_hours": 15,
            "past_project_score": 88.0
        },
        db_path=db_path
    )

    # Demo Faculty
    f_success, f_id = register_user(
        name="Dr. Alan Turing",
        email="faculty@ckin.local",
        password="password123",
        role="faculty",
        extra_data={
            "department": "Computer Science & Engineering",
            "expertise": "Artificial Intelligence, Machine Learning, Software Engineering"
        },
        db_path=db_path
    )

    # Demo Admin
    a_success, a_id = register_user(
        name="System Administrator",
        email="admin@ckin.local",
        password="password123",
        role="admin",
        db_path=db_path
    )

    # Additional Students for Team Recommendation
    student_specs = [
        ("Sarah Chen", "sarah@ckin.local", 4, 9.2, "Python, PyTorch, Deep Learning, NLP, Git", "Artificial Intelligence, NLP", 20, 92.0),
        ("David Miller", "david@ckin.local", 3, 8.1, "JavaScript, React, Node.js, HTML, CSS, MongoDB", "Web Application, Full Stack", 12, 80.0),
        ("Priya Sharma", "priya@ckin.local", 2, 8.5, "Python, SQL, Data Visualization, Pandas, Tableau", "Data Science, Analytics", 15, 85.0),
        ("Marcus Vance", "marcus@ckin.local", 3, 7.9, "Java, Android, Kotlin, Firebase, SQLite", "Mobile Application", 10, 78.0)
    ]

    extra_student_ids = []
    for name, email, year, cgpa, skills, interests, avail, past in student_specs:
        succ, uid = register_user(
            name=name, email=email, password="password123", role="student",
            extra_data={
                "year": year, "cgpa": cgpa, "skills": skills,
                "interests": interests, "availability_hours": avail, "past_project_score": past
            },
            db_path=db_path
        )
        if succ:
            extra_student_ids.append(uid)

    # Get student & faculty IDs for seeding projects
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = 'student@ckin.local'")
    alex_id = cursor.fetchone()['id']

    cursor.execute("SELECT id FROM users WHERE email = 'faculty@ckin.local'")
    faculty_user_id = cursor.fetchone()['id']
    conn.close()

    print("Seeding Initial Projects...")
    # Check if projects already seeded
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM projects")
    p_count = cursor.fetchone()['count']
    conn.close()

    if p_count == 0:
        # Project 1: Approved AI Project
        p1 = create_project(
            creator_id=alex_id,
            title="Campus Knowledge and Innovation Network (CKIN)",
            description="An intelligent web platform for student project discovery, duplicate detection, and ML teammate matching using TF-IDF and NLP.",
            domain="Artificial Intelligence",
            required_skills="Python, Flask, SQLite, Machine Learning, NLP, Scikit-Learn, HTML/CSS",
            difficulty_level="Hard",
            project_type="Web Application",
            weekly_commitment=15,
            team_size=4,
            expected_duration="3 Months",
            db_path=db_path
        )
        approve_project(p1, faculty_user_id, db_path=db_path)

        # Add sample tasks for P1
        create_project_task(p1, "Database Schema Setup", "Design normalized SQLite tables", alex_id, "2026-10-15", db_path=db_path)
        create_project_task(p1, "ML Model Training", "Train scikit-learn recommendation models", alex_id, "2026-10-20", db_path=db_path)

        # Project 2: Approved Data Science Project
        p2 = create_project(
            creator_id=extra_student_ids[0] if extra_student_ids else alex_id,
            title="Smart Campus Energy Management System",
            description="IoT and Machine Learning pipeline for tracking campus electrical grid consumption and predicting power surges.",
            domain="IoT & Analytics",
            required_skills="Python, Pandas, PyTorch, Data Visualization, IoT, SQL",
            difficulty_level="Advanced",
            project_type="Data Science",
            weekly_commitment=12,
            team_size=3,
            expected_duration="4 Months",
            db_path=db_path
        )
        approve_project(p2, faculty_user_id, db_path=db_path)

        # Project 3: Pending Mobile App Project
        p3 = create_project(
            creator_id=extra_student_ids[1] if len(extra_student_ids) > 1 else alex_id,
            title="Campus Lost and Found Finder",
            description="Mobile application for students to report and claim lost items around campus with photo matching.",
            domain="Mobile Application",
            required_skills="Java, Kotlin, Firebase, Android, SQLite",
            difficulty_level="Medium",
            project_type="Mobile Application",
            weekly_commitment=10,
            team_size=3,
            expected_duration="2 Months",
            db_path=db_path
        )
        # Left pending for faculty review demo!

        # Project 4: Completed Web Project
        p4 = create_project(
            creator_id=extra_student_ids[2] if len(extra_student_ids) > 2 else alex_id,
            title="Automated Library Book Reservation Portal",
            description="Web system for digital book requests, automated catalog indexing, and late return notifications.",
            domain="Software Engineering",
            required_skills="JavaScript, HTML, CSS, Node.js, SQL",
            difficulty_level="Easy",
            project_type="Web Application",
            weekly_commitment=8,
            team_size=2,
            expected_duration="2 Months",
            db_path=db_path
        )
        approve_project(p4, faculty_user_id, db_path=db_path)
        
        conn = get_db(db_path)
        conn.execute("UPDATE projects SET status = 'completed' WHERE id = ?", (p4,))
        conn.commit()
        conn.close()

    print("Demo Data Seeding Complete!")

if __name__ == '__main__':
    seed_data()
