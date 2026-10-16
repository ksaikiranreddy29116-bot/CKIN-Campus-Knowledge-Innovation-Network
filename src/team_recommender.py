from src.database import get_db
from src.skill_gap import analyze_skill_gap

def recommend_teammates_for_project(project_id, top_k=5, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()

    # Get project details
    cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    project_row = cursor.fetchone()
    if not project_row:
        conn.close()
        return []
    project = dict(project_row)

    # Get existing member IDs + creator ID
    creator_id = project['creator_id']
    cursor.execute("SELECT student_id FROM project_members WHERE project_id = ?", (project_id,))
    member_ids = {row['student_id'] for row in cursor.fetchall()}
    member_ids.add(creator_id)

    # Fetch all student candidates
    cursor.execute("""
        SELECT u.id, u.name, u.email, sp.*
        FROM users u
        JOIN student_profiles sp ON u.id = sp.user_id
        WHERE u.role = 'student' AND u.is_active = 1
    """)
    candidates = [dict(r) for r in cursor.fetchall() if r['id'] not in member_ids]
    conn.close()

    if not candidates:
        return []

    req_skills = project.get('required_skills', '')
    req_commit = float(project.get('weekly_commitment', 10))

    results = []

    for cand in candidates:
        s_skills = cand.get('skills', '')
        gap = analyze_skill_gap(s_skills, req_skills)
        skill_score = gap['coverage_percentage'] / 100.0

        cgpa = float(cand.get('cgpa', 7.5)) / 10.0
        past_score = float(cand.get('past_project_score', 80.0)) / 100.0
        avail = float(cand.get('availability_hours', 10))
        avail_score = 1.0 if avail >= req_commit else (avail / max(req_commit, 1.0))

        match_score = (0.50 * skill_score) + (0.20 * cgpa) + (0.15 * past_score) + (0.15 * avail_score)
        match_pct = round(match_score * 100, 2)

        matched_skills = gap['matching_skills']
        missing_skills = gap['missing_skills']

        explanation = f"Brings key skills ({', '.join(matched_skills[:3]) if matched_skills else 'General aptitude'}) with {cand.get('availability_hours')} hrs/week availability."

        results.append({
            'student_id': cand['id'],
            'name': cand['name'],
            'email': cand['email'],
            'year': cand['year'],
            'cgpa': cand['cgpa'],
            'skills': cand['skills'],
            'availability_hours': cand['availability_hours'],
            'match_score': round(match_score, 4),
            'match_percentage': match_pct,
            'matched_skills': matched_skills,
            'missing_skills': missing_skills,
            'explanation': explanation
        })

    results.sort(key=lambda x: x['match_score'], reverse=True)
    return results[:top_k]
