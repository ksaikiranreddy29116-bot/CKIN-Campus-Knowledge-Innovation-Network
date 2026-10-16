def normalize_skill(skill):
    return skill.strip().lower()

def analyze_skill_gap(student_skills_str, project_skills_str):
    if isinstance(student_skills_str, list):
        s_skills = [normalize_skill(s) for s in student_skills_str if s]
    else:
        s_skills = [normalize_skill(s) for s in (student_skills_str or '').split(',') if s.strip()]

    if isinstance(project_skills_str, list):
        p_skills_raw = [s.strip() for s in project_skills_str if s]
    else:
        p_skills_raw = [s.strip() for s in (project_skills_str or '').split(',') if s.strip()]

    p_skills_norm = [normalize_skill(s) for s in p_skills_raw]

    matching = []
    missing = []
    
    for raw, norm in zip(p_skills_raw, p_skills_norm):
        if any(norm == s or norm in s or s in norm for s in s_skills):
            matching.append(raw)
        else:
            missing.append(raw)

    total_req = len(p_skills_raw)
    coverage_pct = round((len(matching) / total_req * 100), 2) if total_req > 0 else 100.0

    suggestion = "You have all required skills for this project!"
    if missing:
        suggestion = f"Recommended learning path: Focus on acquiring skills in {', '.join(missing)} to increase readiness."

    return {
        'required_skills': p_skills_raw,
        'matching_skills': matching,
        'missing_skills': missing,
        'coverage_percentage': coverage_pct,
        'matching_count': len(matching),
        'total_count': total_req,
        'learning_suggestion': suggestion
    }
