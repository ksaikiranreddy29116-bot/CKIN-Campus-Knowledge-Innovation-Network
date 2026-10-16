import os
import joblib
import numpy as np
from config import Config
from src.database import get_db
from src.feature_engineering import extract_features
from src.similarity_engine import compute_project_text, find_similar_projects
from src.skill_gap import analyze_skill_gap
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_MODEL_CACHE = None

def load_ml_model(models_dir=None):
    global _MODEL_CACHE
    if _MODEL_CACHE is not None:
        return _MODEL_CACHE

    target_dir = models_dir or Config.MODELS_DIR
    model_path = os.path.join(target_dir, 'recommendation_model.joblib')

    if os.path.exists(model_path):
        try:
            artifact = joblib.load(model_path)
            _MODEL_CACHE = artifact.get('model')
            return _MODEL_CACHE
        except Exception as e:
            print(f"Warning: Could not load trained model artifact: {e}")

    return None

def compute_heuristic_compatibility(student_profile, project):
    s_skills = student_profile.get('skills', '')
    p_skills = project.get('required_skills', '')
    gap = analyze_skill_gap(s_skills, p_skills)
    skill_pct = gap['coverage_percentage'] / 100.0

    s_interests = (student_profile.get('interests', '') or '').lower()
    p_domain = (project.get('domain', '') or '').lower()
    domain_match = 1.0 if (p_domain in s_interests or any(w in s_interests for w in p_domain.split())) else 0.5

    avail = float(student_profile.get('availability_hours', 10))
    commit = float(project.get('weekly_commitment', 10))
    avail_match = 1.0 if avail >= commit else (avail / max(commit, 1.0))

    comp_score = 0.50 * skill_pct + 0.30 * domain_match + 0.20 * avail_match
    return round(float(comp_score), 4)

def get_recommendations_for_student(student_id, top_k=5, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()

    # Get student profile
    cursor.execute("""
        SELECT u.id, u.name, sp.*
        FROM users u
        JOIN student_profiles sp ON u.id = sp.user_id
        WHERE u.id = ?
    """, (student_id,))
    student_row = cursor.fetchone()
    if not student_row:
        conn.close()
        return []
    student = dict(student_row)

    # Get projects student is already a member of or creator of
    cursor.execute("SELECT id FROM projects WHERE creator_id = ?", (student_id,))
    created_ids = {row['id'] for row in cursor.fetchall()}

    cursor.execute("SELECT project_id FROM project_members WHERE student_id = ?", (student_id,))
    member_ids = {row['project_id'] for row in cursor.fetchall()}

    excluded_ids = created_ids.union(member_ids)

    # Fetch candidate projects (approved status)
    cursor.execute("""
        SELECT p.*, u.name as creator_name
        FROM projects p
        JOIN users u ON p.creator_id = u.id
        WHERE p.status = 'approved'
    """)
    candidate_projects = [dict(r) for r in cursor.fetchall() if r['id'] not in excluded_ids]

    if not candidate_projects:
        conn.close()
        return []

    model = load_ml_model()

    # Prepare TF-IDF text similarity between student skills/interests and project description/skills
    student_text = f"{student.get('skills', '')} {student.get('interests', '')} {student.get('preferred_project_type', '')}".lower()
    project_texts = [compute_project_text(p) for p in candidate_projects]

    text_sim_scores = np.zeros(len(candidate_projects))
    if student_text.strip():
        corpus = [student_text] + project_texts
        try:
            vec = TfidfVectorizer(stop_words='english')
            tfidf = vec.fit_transform(corpus)
            text_sim_scores = cosine_similarity(tfidf[0:1], tfidf[1:])[0]
        except Exception:
            text_sim_scores = np.zeros(len(candidate_projects))

    recommendations = []

    for idx, proj in enumerate(candidate_projects):
        text_sim = float(text_sim_scores[idx])
        comp_score = compute_heuristic_compatibility(student, proj)

        # Feature vector for ML
        feature_vec = extract_features(student, proj, text_sim_score=text_sim)

        if model is not None:
            try:
                proba = model.predict_proba(feature_vec.reshape(1, -1))[0][1]
                ml_score = float(proba)
            except Exception:
                ml_score = comp_score
        else:
            ml_score = comp_score

        # Hybrid Score: 0.35 * Compatibility + 0.45 * ML + 0.20 * Text Similarity
        final_score = (0.35 * comp_score) + (0.45 * ml_score) + (0.20 * text_sim)
        final_pct = round(final_score * 100, 2)

        # Gap details
        gap_info = analyze_skill_gap(student.get('skills', ''), proj.get('required_skills', ''))

        explanation_parts = []
        if gap_info['matching_skills']:
            explanation_parts.append(f"Matches your skills ({', '.join(gap_info['matching_skills'][:3])})")
        if text_sim > 0.2:
            explanation_parts.append("Aligns with your interests and project domain")
        if comp_score > 0.7:
            explanation_parts.append("Fits your availability and academic level")

        explanation = ". ".join(explanation_parts) + "." if explanation_parts else "Good overall project match."

        rec_item = {
            'project_id': proj['id'],
            'title': proj['title'],
            'description': proj['description'],
            'domain': proj['domain'],
            'required_skills': proj['required_skills'],
            'difficulty_level': proj['difficulty_level'],
            'creator_name': proj['creator_name'],
            'compatibility_score': round(comp_score, 4),
            'ml_score': round(ml_score, 4),
            'similarity_score': round(text_sim, 4),
            'final_score': round(final_score, 4),
            'final_percentage': final_pct,
            'explanation': explanation,
            'gap_info': gap_info
        }

        recommendations.append(rec_item)

        # Save to recommendation_history table
        cursor.execute("""
            INSERT INTO recommendation_history
            (student_id, project_id, compatibility_score, ml_score, similarity_score, final_score)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (student_id, proj['id'], comp_score, ml_score, text_sim, final_score))

    conn.commit()
    conn.close()

    recommendations.sort(key=lambda x: x['final_score'], reverse=True)
    return recommendations[:top_k]
