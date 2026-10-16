from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from src.database import get_db

def compute_project_text(p):
    title = p.get('title', '') or ''
    description = p.get('description', '') or ''
    domain = p.get('domain', '') or ''
    skills = p.get('required_skills', '') or ''
    p_type = p.get('project_type', '') or ''
    
    # Weight title and skills heavier by repeating them
    text = f"{title} {title} {skills} {skills} {domain} {p_type} {description}"
    return text.strip().lower()

def find_similar_projects(target_project, current_project_id=None, threshold=0.1, top_k=5, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT p.*, u.name as creator_name
        FROM projects p
        JOIN users u ON p.creator_id = u.id
        WHERE p.status IN ('approved', 'pending', 'completed')
    """)
    all_projects = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Filter out current project if updating or checking against DB
    if current_project_id:
        all_projects = [p for p in all_projects if p['id'] != int(current_project_id)]

    if not all_projects:
        return []

    target_text = compute_project_text(target_project)
    if not target_text:
        return []

    corpus = [target_text] + [compute_project_text(p) for p in all_projects]

    vectorizer = TfidfVectorizer(stop_words='english')
    try:
        tfidf_matrix = vectorizer.fit_transform(corpus)
    except Exception:
        # If corpus is empty or only stop words
        return []

    target_vec = tfidf_matrix[0:1]
    projects_vec = tfidf_matrix[1:]

    sim_scores = cosine_similarity(target_vec, projects_vec)[0]

    similar_results = []
    feature_names = set(vectorizer.get_feature_names_out())

    for idx, score in enumerate(sim_scores):
        if score >= threshold:
            proj = all_projects[idx]
            
            # Simple keyword match detection for explanation
            target_words = set(target_text.split())
            proj_words = set(compute_project_text(proj).split())
            common_words = list(target_words.intersection(proj_words).intersection(feature_names))[:5]
            
            explanation = "Overlapping topic and technology terms."
            if common_words:
                explanation = f"Shared key terms: {', '.join(common_words)}"

            similar_results.append({
                'project_id': proj['id'],
                'title': proj['title'],
                'creator_name': proj['creator_name'],
                'domain': proj['domain'],
                'required_skills': proj['required_skills'],
                'status': proj['status'],
                'similarity_score': round(float(score), 4),
                'similarity_percentage': round(float(score) * 100, 2),
                'common_keywords': common_words,
                'explanation': explanation
            })

    # Sort descending by similarity score
    similar_results.sort(key=lambda x: x['similarity_score'], reverse=True)
    return similar_results[:top_k]
