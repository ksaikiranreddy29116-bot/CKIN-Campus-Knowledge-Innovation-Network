import numpy as np
from src.skill_gap import analyze_skill_gap

DIFFICULTY_MAP = {'Easy': 1, 'Medium': 2, 'Hard': 3, 'Advanced': 4}

def extract_features(student_profile, project, text_sim_score=0.0):
    year = float(student_profile.get('year', 3))
    cgpa = float(student_profile.get('cgpa', 8.0))
    avail_hours = float(student_profile.get('availability_hours', 10))
    past_score = float(student_profile.get('past_project_score', 80.0))

    diff_str = project.get('difficulty_level', 'Medium')
    difficulty = float(DIFFICULTY_MAP.get(diff_str, 2))
    commitment = float(project.get('weekly_commitment', 10))
    team_size = float(project.get('team_size', 4))

    # Skill match
    s_skills = student_profile.get('skills', '')
    p_skills = project.get('required_skills', '')
    gap_res = analyze_skill_gap(s_skills, p_skills)
    
    skill_match_ratio = gap_res['coverage_percentage'] / 100.0
    missing_skills_count = float(len(gap_res['missing_skills']))

    # Domain match
    s_interests = (student_profile.get('interests', '') or '').lower()
    p_domain = (project.get('domain', '') or '').lower()
    domain_match = 1.0 if (p_domain in s_interests or any(w in s_interests for w in p_domain.split())) else 0.0

    # Project type match
    s_pref_type = (student_profile.get('preferred_project_type', '') or '').lower()
    p_type = (project.get('project_type', '') or '').lower()
    type_match = 1.0 if (s_pref_type == p_type or s_pref_type in p_type or p_type in s_pref_type) else 0.0

    # Fit metrics
    commitment_fit = 1.0 if avail_hours >= commitment else (avail_hours / max(commitment, 1.0))
    cgpa_fit = min(cgpa / 10.0, 1.0)
    difficulty_fit = 1.0 if (year >= 3 or difficulty <= 2) else 0.6

    feature_vector = [
        year,
        cgpa,
        avail_hours,
        past_score,
        difficulty,
        commitment,
        team_size,
        skill_match_ratio,
        missing_skills_count,
        domain_match,
        type_match,
        commitment_fit,
        cgpa_fit,
        difficulty_fit,
        float(text_sim_score)
    ]

    return np.array(feature_vector, dtype=np.float32)

FEATURE_NAMES = [
    'year', 'cgpa', 'availability_hours', 'past_project_score',
    'difficulty_level', 'weekly_commitment', 'team_size',
    'skill_match_ratio', 'missing_skills_count', 'domain_match',
    'type_match', 'commitment_fit', 'cgpa_fit', 'difficulty_fit',
    'text_sim_score'
]
