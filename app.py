import os
import io
import csv
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, Response
from config import Config
from src.database import init_db, get_db
from src.auth import authenticate_user, register_user, get_user_by_id
from src.project_service import (
    create_project, get_project_by_id, list_projects, approve_project, reject_project,
    get_project_members, create_join_request, handle_join_request, cancel_join_request,
    create_team_invitation, handle_team_invitation, cancel_team_invitation,
    get_user_invitations, get_user_join_requests, get_project_join_requests,
    create_project_task, update_task_details, update_task_progress, delete_project_task, get_project_tasks,
    create_project_comment, get_project_comments, delete_project_comment,
    create_project_resource, get_project_resources, delete_project_resource,
    create_project_milestone, get_project_milestones, update_milestone_status, delete_project_milestone
)
from src.similarity_engine import find_similar_projects
from src.recommendation_engine import get_recommendations_for_student, compute_heuristic_compatibility
from src.team_recommender import recommend_teammates_for_project
from src.skill_gap import analyze_skill_gap
from src.notification_service import get_user_notifications, mark_notification_read, mark_all_notifications_read
from src.activity_service import get_recent_activities, log_activity

app = Flask(__name__)
app.config.from_object(Config)

# Ensure DB initialized on start
with app.app_context():
    init_db()

# --- Authorization Decorators ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Authentication required.'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                if request.path.startswith('/api/'):
                    return jsonify({'success': False, 'error': 'Authentication required.'}), 401
                return redirect(url_for('login'))
            if session.get('role') not in allowed_roles:
                if request.path.startswith('/api/'):
                    return jsonify({'success': False, 'error': 'Unauthorized role access.'}), 403
                flash("You do not have permission to access that resource.", "danger")
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Context Processors ---
@app.context_processor
def inject_user_context():
    if 'user_id' in session:
        user = get_user_by_id(session['user_id'])
        notifs = get_user_notifications(session['user_id'], unread_only=True)
        return {'current_user': user, 'unread_notifications_count': len(notifs)}
    return {'current_user': None, 'unread_notifications_count': 0}

# --- Page Routes ---
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        user, msg = authenticate_user(email, password)
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['role'] = user['role']
            log_activity(user['id'], "LOGIN", "user", user['id'], f"User logged in ({user['role']})")
            return redirect(url_for('dashboard'))
        else:
            flash(msg, 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'student')
        
        extra_data = {}
        if role == 'student':
            extra_data = {
                'year': int(request.form.get('year', 1)),
                'cgpa': float(request.form.get('cgpa', 7.5)),
                'skills': request.form.get('skills', ''),
                'interests': request.form.get('interests', ''),
                'preferred_project_type': request.form.get('preferred_project_type', 'Web Application'),
                'availability_hours': int(request.form.get('availability_hours', 10)),
                'past_project_score': float(request.form.get('past_project_score', 80.0))
            }

        success, res = register_user(name, email, password, role, extra_data)
        if success:
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
        else:
            flash(f"Registration failed: {res}", "danger")
    return render_template('register.html')

@app.route('/logout')
def logout():
    if 'user_id' in session:
        log_activity(session['user_id'], "LOGOUT", "user", session['user_id'], "User logged out")
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    role = session.get('role')
    if role == 'student':
        return redirect(url_for('student_dashboard'))
    elif role == 'faculty':
        return redirect(url_for('faculty_dashboard'))
    elif role == 'admin':
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('login'))

@app.route('/student/dashboard')
@role_required('student')
def student_dashboard():
    user_id = session['user_id']
    user = get_user_by_id(user_id)
    my_projects = list_projects(creator_id=user_id)
    approved_projects = list_projects(status='approved')[:6]
    recommendations = get_recommendations_for_student(user_id, top_k=3)
    invitations = get_user_invitations(user_id)
    pending_invites = [i for i in invitations if i['status'] == 'pending']

    return render_template(
        'student_dashboard.html',
        student=user,
        my_projects=my_projects,
        approved_projects=approved_projects,
        recommendations=recommendations,
        pending_invites=pending_invites
    )

@app.route('/faculty/dashboard')
@role_required('faculty')
def faculty_dashboard():
    pending_projects = list_projects(status='pending')
    approved_projects = list_projects(status='approved')
    rejected_projects = list_projects(status='rejected')
    recent_activities = get_recent_activities(limit=10)

    # Attach similarity reports to pending projects for quick review
    for p in pending_projects:
        p['similar_projects'] = find_similar_projects(p, current_project_id=p['id'], top_k=3)

    return render_template(
        'faculty_dashboard.html',
        pending_projects=pending_projects,
        approved_projects=approved_projects,
        rejected_projects=rejected_projects,
        recent_activities=recent_activities
    )

@app.route('/admin/dashboard')
@role_required('admin')
def admin_dashboard():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'student'")
    student_count = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'faculty'")
    faculty_count = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM projects")
    total_projects = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM projects WHERE status = 'pending'")
    pending_count = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM projects WHERE status = 'approved'")
    approved_count = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM projects WHERE status = 'rejected'")
    rejected_count = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM projects WHERE status = 'completed'")
    completed_count = cursor.fetchone()['count']

    cursor.execute("SELECT id, name, email, role, created_at, is_active FROM users ORDER BY created_at DESC LIMIT 20")
    recent_users = [dict(r) for r in cursor.fetchall()]

    conn.close()
    recent_activities = get_recent_activities(limit=20)

    metrics = {
        'student_count': student_count,
        'faculty_count': faculty_count,
        'total_projects': total_projects,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'completed_count': completed_count
    }

    return render_template(
        'admin_dashboard.html',
        metrics=metrics,
        recent_users=recent_users,
        recent_activities=recent_activities
    )

@app.route('/projects')
@login_required
def projects():
    status = request.args.get('status', '')
    domain = request.args.get('domain', '')
    p_type = request.args.get('type', '')
    search = request.args.get('search', '')

    all_projects = list_projects(
        status=status or None,
        domain=domain or None,
        project_type=p_type or None,
        search=search or None
    )

    return render_template('projects.html', projects=all_projects, status=status, domain=domain, p_type=p_type, search=search)

@app.route('/projects/<int:project_id>')
@login_required
def project_detail(project_id):
    project = get_project_by_id(project_id)
    if not project:
        return render_template('error.html', message="Project not found."), 404

    members = get_project_members(project_id)
    similar_projects = find_similar_projects(project, current_project_id=project_id, top_k=5)
    tasks = get_project_tasks(project_id)

    user_id = session['user_id']
    is_member = any(m['student_id'] == user_id for m in members)
    is_creator = (project['creator_id'] == user_id)

    teammate_recs = []
    if is_creator and session.get('role') == 'student':
        teammate_recs = recommend_teammates_for_project(project_id, top_k=5)

    user_profile = get_user_by_id(user_id)
    gap_info = {}
    if user_profile and user_profile.get('profile'):
        gap_info = analyze_skill_gap(user_profile['profile'].get('skills', ''), project['required_skills'])

    join_requests = []
    if is_creator or session.get('role') in ['faculty', 'admin']:
        join_requests = get_project_join_requests(project_id)

    comments = get_project_comments(project_id)
    resources = get_project_resources(project_id)
    milestones = get_project_milestones(project_id)

    return render_template(
        'project_detail.html',
        project=project,
        members=members,
        similar_projects=similar_projects,
        tasks=tasks,
        is_member=is_member,
        is_creator=is_creator,
        teammate_recs=teammate_recs,
        gap_info=gap_info,
        join_requests=join_requests,
        comments=comments,
        resources=resources,
        milestones=milestones
    )

@app.route('/projects/create', methods=['GET', 'POST'])
@role_required('student')
def create_project_page():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        domain = request.form.get('domain', '').strip()
        required_skills = request.form.get('required_skills', '').strip()
        difficulty_level = request.form.get('difficulty_level', 'Medium')
        project_type = request.form.get('project_type', 'Web Application')
        weekly_commitment = int(request.form.get('weekly_commitment', 10))
        team_size = int(request.form.get('team_size', 4))
        expected_duration = request.form.get('expected_duration', '3 Months')

        if not title or not description or not domain or not required_skills:
            flash("Please fill in all required fields.", "danger")
            return render_template('create_project.html')

        user_id = session['user_id']
        project_id = create_project(
            creator_id=user_id,
            title=title,
            description=description,
            domain=domain,
            required_skills=required_skills,
            difficulty_level=difficulty_level,
            project_type=project_type,
            weekly_commitment=weekly_commitment,
            team_size=team_size,
            expected_duration=expected_duration
        )

        flash("Project created successfully and submitted for faculty review!", "success")
        return redirect(url_for('project_detail', project_id=project_id))

    return render_template('create_project.html')

@app.route('/recommendations')
@role_required('student')
def recommendations_page():
    user_id = session['user_id']
    recommendations = get_recommendations_for_student(user_id, top_k=10)
    user = get_user_by_id(user_id)
    return render_template('recommendations.html', recommendations=recommendations, student=user)

@app.route('/my-team')
@role_required('student')
def my_team_page():
    user_id = session['user_id']
    my_projects = list_projects(creator_id=user_id)
    invitations = get_user_invitations(user_id)
    join_requests = get_user_join_requests(user_id)

    return render_template('my_team.html', my_projects=my_projects, invitations=invitations, join_requests=join_requests)

@app.route('/notifications')
@login_required
def notifications_page():
    user_id = session['user_id']
    notifications = get_user_notifications(user_id)
    return render_template('notifications.html', notifications=notifications)

@app.route('/tasks')
@login_required
def tasks_page():
    user_id = session['user_id']
    role = session.get('role')

    filter_project = request.args.get('project_id', '')
    filter_status = request.args.get('status', '')
    filter_priority = request.args.get('priority', '')
    filter_assignee = request.args.get('assigned_to', '')

    if role == 'student':
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT p.* FROM projects p
            LEFT JOIN project_members pm ON p.id = pm.project_id
            WHERE p.creator_id = ? OR pm.student_id = ?
        """, (user_id, user_id))
        user_projects = [dict(r) for r in cursor.fetchall()]
        conn.close()
    else:
        user_projects = list_projects()

    all_tasks = []
    project_stats = {}
    today_str = datetime.now().strftime('%Y-%m-%d')

    for p in user_projects:
        p_tasks = get_project_tasks(p['id'])
        total_p = len(p_tasks)
        comp_p = sum(1 for t in p_tasks if t['status'] == 'completed')
        pct_p = round((comp_p / total_p * 100), 1) if total_p > 0 else 0.0
        project_stats[p['id']] = {
            'total': total_p,
            'completed': comp_p,
            'completion_pct': pct_p
        }

        for t in p_tasks:
            t['project_title'] = p['title']
            t['is_overdue'] = False
            if t.get('due_date') and t['status'] != 'completed' and t['due_date'] < today_str:
                t['is_overdue'] = True
            all_tasks.append(t)

    filtered_tasks = all_tasks
    if filter_project:
        filtered_tasks = [t for t in filtered_tasks if str(t['project_id']) == filter_project]
    if filter_status:
        filtered_tasks = [t for t in filtered_tasks if t['status'] == filter_status]
    if filter_priority:
        filtered_tasks = [t for t in filtered_tasks if t.get('priority', 'Medium') == filter_priority]
    if filter_assignee:
        filtered_tasks = [t for t in filtered_tasks if str(t.get('assigned_to', '')) == filter_assignee]

    all_members = []
    member_ids = set()
    for p in user_projects:
        for m in get_project_members(p['id']):
            if m['student_id'] not in member_ids:
                member_ids.add(m['student_id'])
                all_members.append({'id': m['student_id'], 'name': m['name']})

    return render_template(
        'tasks.html',
        tasks=filtered_tasks,
        all_tasks=all_tasks,
        user_projects=user_projects,
        project_stats=project_stats,
        team_members=all_members,
        filter_project=filter_project,
        filter_status=filter_status,
        filter_priority=filter_priority,
        filter_assignee=filter_assignee
    )

@app.route('/profile')
@login_required
def profile_page():
    user = get_user_by_id(session['user_id'])
    return render_template('profile.html', user=user)

# --- API Endpoints ---
@app.route('/api/projects', methods=['GET'])
def api_list_projects():
    status = request.args.get('status')
    domain = request.args.get('domain')
    p_type = request.args.get('type')
    search = request.args.get('search')
    projs = list_projects(status=status, domain=domain, project_type=p_type, search=search)
    return jsonify({'success': True, 'data': projs})

@app.route('/api/projects/<int:project_id>', methods=['GET'])
def api_get_project(project_id):
    proj = get_project_by_id(project_id)
    if not proj:
        return jsonify({'success': False, 'error': 'Project not found'}), 404
    members = get_project_members(project_id)
    tasks = get_project_tasks(project_id)
    return jsonify({'success': True, 'data': {'project': proj, 'members': members, 'tasks': tasks}})

@app.route('/api/projects/<int:project_id>/similarity', methods=['GET'])
def api_project_similarity(project_id):
    proj = get_project_by_id(project_id)
    if not proj:
        return jsonify({'success': False, 'error': 'Project not found'}), 404
    similar = find_similar_projects(proj, current_project_id=project_id, top_k=5)
    return jsonify({'success': True, 'data': similar})

@app.route('/api/projects/<int:project_id>/approve', methods=['POST'])
@role_required('faculty')
def api_approve_project(project_id):
    faculty_id = session['user_id']
    success, msg = approve_project(project_id, faculty_id)
    if success:
        return jsonify({'success': True, 'message': msg})
    return jsonify({'success': False, 'error': msg}), 400

@app.route('/api/projects/<int:project_id>/reject', methods=['POST'])
@role_required('faculty')
def api_reject_project(project_id):
    faculty_id = session['user_id']
    data = request.get_json() or {}
    rejection_reason = data.get('rejection_reason', request.form.get('rejection_reason', '')).strip()
    success, msg = reject_project(project_id, faculty_id, rejection_reason=rejection_reason)
    if success:
        return jsonify({'success': True, 'message': msg})
    return jsonify({'success': False, 'error': msg}), 400
    return jsonify({'success': False, 'error': msg}), 400

@app.route('/api/recommendations/projects', methods=['GET'])
@role_required('student')
def api_recommend_projects():
    user_id = session['user_id']
    recs = get_recommendations_for_student(user_id, top_k=5)
    return jsonify({'success': True, 'data': recs})

@app.route('/api/recommendations/teammates/<int:project_id>', methods=['GET'])
@role_required('student')
def api_recommend_teammates(project_id):
    recs = recommend_teammates_for_project(project_id, top_k=5)
    return jsonify({'success': True, 'data': recs})

@app.route('/api/recommendations/simulate', methods=['POST'])
@role_required('student')
def api_simulate_skill():
    data = request.get_json() or {}
    project_id = data.get('project_id')
    hypothetical_skill = data.get('skill', '').strip()

    if not project_id or not hypothetical_skill:
        return jsonify({'success': False, 'error': 'Project ID and hypothetical skill required.'}), 400

    proj = get_project_by_id(project_id)
    if not proj:
        return jsonify({'success': False, 'error': 'Project not found'}), 404

    user = get_user_by_id(session['user_id'])
    current_skills = user['profile'].get('skills', '') if user.get('profile') else ''

    # Original Gap Analysis & Compatibility
    orig_gap = analyze_skill_gap(current_skills, proj['required_skills'])
    orig_comp = compute_heuristic_compatibility(user['profile'], proj)

    # Simulated Skills
    simulated_skills = f"{current_skills}, {hypothetical_skill}"
    sim_gap = analyze_skill_gap(simulated_skills, proj['required_skills'])

    sim_user_profile = dict(user['profile'])
    sim_user_profile['skills'] = simulated_skills
    sim_comp = compute_heuristic_compatibility(sim_user_profile, proj)

    comp_diff = round((sim_comp - orig_comp) * 100, 2)

    return jsonify({
        'success': True,
        'data': {
            'hypothetical_skill': hypothetical_skill,
            'original_coverage_percentage': orig_gap['coverage_percentage'],
            'simulated_coverage_percentage': sim_gap['coverage_percentage'],
            'original_compatibility_pct': round(orig_comp * 100, 2),
            'simulated_compatibility_pct': round(sim_comp * 100, 2),
            'score_difference_pct': comp_diff,
            'simulated_missing_skills': sim_gap['missing_skills']
        }
    })

@app.route('/api/collaboration/invite', methods=['POST'])
@role_required('student')
def api_invite_student():
    data = request.get_json() or {}
    project_id = data.get('project_id')
    invitee_id = data.get('invitee_id')
    inviter_id = session['user_id']

    if not project_id or not invitee_id:
        return jsonify({'success': False, 'error': 'Project ID and Invitee ID required.'}), 400

    success, msg = create_team_invitation(project_id, inviter_id, invitee_id)
    if success:
        return jsonify({'success': True, 'message': msg})
    return jsonify({'success': False, 'error': msg}), 400

@app.route('/api/collaboration/invitations/<int:inv_id>/respond', methods=['POST'])
@role_required('student')
def api_respond_invitation(inv_id):
    data = request.get_json() or {}
    action = data.get('action')  # accept or decline
    user_id = session['user_id']

    if action not in ['accept', 'decline']:
        return jsonify({'success': False, 'error': 'Invalid action'}), 400

    success, msg = handle_team_invitation(inv_id, action, user_id)
    if success:
        return jsonify({'success': True, 'message': msg})
    return jsonify({'success': False, 'error': msg}), 400

@app.route('/api/collaboration/join-request', methods=['POST'])
@role_required('student')
def api_submit_join_request():
    data = request.get_json() or {}
    project_id = data.get('project_id')
    message = data.get('message', '')
    student_id = session['user_id']

    if not project_id:
        return jsonify({'success': False, 'error': 'Project ID required'}), 400

    success, msg = create_join_request(project_id, student_id, message)
    if success:
        return jsonify({'success': True, 'message': msg})
    return jsonify({'success': False, 'error': msg}), 400

@app.route('/api/collaboration/join-requests/<int:req_id>/respond', methods=['POST'])
@role_required('student')
def api_respond_join_request(req_id):
    data = request.get_json() or {}
    action = data.get('action') # accept or reject
    user_id = session['user_id']

    if action not in ['accept', 'reject']:
        return jsonify({'success': False, 'error': 'Invalid action'}), 400

    success, msg = handle_join_request(req_id, action, user_id)
    if success:
        return jsonify({'success': True, 'message': msg})
    return jsonify({'success': False, 'error': msg}), 400

@app.route('/api/tasks/<int:project_id>', methods=['GET', 'POST'])
@login_required
def api_project_tasks(project_id):
    proj = get_project_by_id(project_id)
    if not proj:
        return jsonify({'success': False, 'error': 'Project not found.'}), 404

    if request.method == 'POST':
        user_id = session['user_id']
        role = session.get('role')

        members = get_project_members(project_id)
        is_member = any(m['student_id'] == user_id for m in members)
        is_creator = (proj['creator_id'] == user_id)

        if not (is_member or is_creator or role in ['faculty', 'admin']):
            return jsonify({'success': False, 'error': 'Unauthorized to create tasks for this project.'}), 403

        data = request.get_json() or {}
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        assigned_to_raw = data.get('assigned_to')
        due_date = data.get('due_date', '').strip()
        status = data.get('status', 'pending')
        progress_raw = data.get('progress', 0)

        if not title:
            return jsonify({'success': False, 'error': 'Task title is required.'}), 400

        try:
            progress = int(progress_raw)
            if progress < 0 or progress > 100:
                return jsonify({'success': False, 'error': 'Progress must be a numeric value between 0 and 100.'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Progress must be a valid integer between 0 and 100.'}), 400

        assigned_to = None
        if assigned_to_raw:
            try:
                assigned_to = int(assigned_to_raw)
            except (ValueError, TypeError):
                assigned_to = None

        priority = data.get('priority', 'Medium')

        task_id = create_project_task(
            project_id=project_id,
            title=title,
            description=description,
            assigned_to=assigned_to,
            due_date=due_date,
            status=status,
            progress=progress,
            priority=priority
        )
        return jsonify({'success': True, 'task_id': task_id, 'message': 'Task created successfully.'})
    
    tasks = get_project_tasks(project_id)
    return jsonify({'success': True, 'data': tasks})

@app.route('/api/tasks/<int:task_id>/edit', methods=['POST'])
@login_required
def api_edit_task(task_id):
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    assigned_to_raw = data.get('assigned_to')
    due_date = data.get('due_date', '').strip()
    status = data.get('status', 'pending')
    progress_raw = data.get('progress', 0)
    priority = data.get('priority', 'Medium')

    if not title:
        return jsonify({'success': False, 'error': 'Title is required'}), 400

    try:
        progress = int(progress_raw)
        if progress < 0 or progress > 100:
            return jsonify({'success': False, 'error': 'Progress must be 0-100'}), 400
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Invalid progress value'}), 400

    assigned_to = int(assigned_to_raw) if assigned_to_raw else None

    success, msg = update_task_details(task_id, title, description, assigned_to, due_date, status, progress, priority)
    if success:
        return jsonify({'success': True, 'message': msg})
    return jsonify({'success': False, 'error': msg}), 400

@app.route('/api/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def api_delete_task(task_id):
    success, msg = delete_project_task(task_id)
    if success:
        return jsonify({'success': True, 'message': msg})
    return jsonify({'success': False, 'error': msg}), 400

@app.route('/api/tasks/<int:task_id>/progress', methods=['POST'])
@login_required
def api_update_task_progress(task_id):
    data = request.get_json() or {}
    status = data.get('status', 'pending')
    progress_raw = data.get('progress', 0)

    try:
        progress = int(progress_raw)
        if progress < 0 or progress > 100:
            return jsonify({'success': False, 'error': 'Progress must be between 0 and 100.'}), 400
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Invalid progress value.'}), 400

    if status not in ['pending', 'in_progress', 'completed']:
        status = 'pending'

    update_task_progress(task_id, status, progress)
    return jsonify({'success': True, 'message': 'Task updated successfully.'})

# --- Invitations and Join Requests Cancellation ---
@app.route('/api/collaboration/invitations/<int:inv_id>/cancel', methods=['POST'])
@login_required
def api_cancel_invitation(inv_id):
    success, msg = cancel_team_invitation(inv_id, session['user_id'])
    if success:
        return jsonify({'success': True, 'message': msg})
    return jsonify({'success': False, 'error': msg}), 400

@app.route('/api/collaboration/join-requests/<int:req_id>/cancel', methods=['POST'])
@login_required
def api_cancel_join_request(req_id):
    success, msg = cancel_join_request(req_id, session['user_id'])
    if success:
        return jsonify({'success': True, 'message': msg})
    return jsonify({'success': False, 'error': msg}), 400

# --- Project Comments ---
@app.route('/api/projects/<int:project_id>/comments', methods=['GET', 'POST'])
@login_required
def api_project_comments(project_id):
    if request.method == 'POST':
        data = request.get_json() or {}
        comment_text = data.get('comment_text', '').strip()
        success, res = create_project_comment(project_id, session['user_id'], comment_text)
        if success:
            return jsonify({'success': True, 'comment_id': res, 'message': 'Comment posted.'})
        return jsonify({'success': False, 'error': res}), 400

    comments = get_project_comments(project_id)
    return jsonify({'success': True, 'data': comments})

@app.route('/api/comments/<int:comment_id>/delete', methods=['POST'])
@login_required
def api_delete_comment(comment_id):
    success, msg = delete_project_comment(comment_id, session['user_id'], session.get('role'))
    if success:
        return jsonify({'success': True, 'message': msg})
    return jsonify({'success': False, 'error': msg}), 400

# --- Project Resources ---
@app.route('/api/projects/<int:project_id>/resources', methods=['GET', 'POST'])
@login_required
def api_project_resources(project_id):
    if request.method == 'POST':
        data = request.get_json() or {}
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        resource_url = data.get('resource_url', '').strip()
        success, res = create_project_resource(project_id, session['user_id'], title, description, resource_url)
        if success:
            return jsonify({'success': True, 'resource_id': res, 'message': 'Resource added.'})
        return jsonify({'success': False, 'error': res}), 400

    resources = get_project_resources(project_id)
    return jsonify({'success': True, 'data': resources})

@app.route('/api/resources/<int:resource_id>/delete', methods=['POST'])
@login_required
def api_delete_resource(resource_id):
    success, msg = delete_project_resource(resource_id, session['user_id'], session.get('role'))
    if success:
        return jsonify({'success': True, 'message': msg})
    return jsonify({'success': False, 'error': msg}), 400

# --- Project Milestones ---
@app.route('/api/projects/<int:project_id>/milestones', methods=['GET', 'POST'])
@login_required
def api_project_milestones(project_id):
    if request.method == 'POST':
        data = request.get_json() or {}
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        due_date = data.get('due_date', '').strip()
        success, res = create_project_milestone(project_id, title, description, due_date)
        if success:
            return jsonify({'success': True, 'milestone_id': res, 'message': 'Milestone created.'})
        return jsonify({'success': False, 'error': res}), 400

    milestones = get_project_milestones(project_id)
    return jsonify({'success': True, 'data': milestones})

@app.route('/api/milestones/<int:milestone_id>/status', methods=['POST'])
@login_required
def api_update_milestone_status(milestone_id):
    data = request.get_json() or {}
    status = data.get('status', 'pending')
    success, msg = update_milestone_status(milestone_id, status)
    if success:
        return jsonify({'success': True, 'message': msg})
    return jsonify({'success': False, 'error': msg}), 400

@app.route('/api/milestones/<int:milestone_id>/delete', methods=['POST'])
@login_required
def api_delete_milestone(milestone_id):
    success, msg = delete_project_milestone(milestone_id)
    if success:
        return jsonify({'success': True, 'message': msg})
    return jsonify({'success': False, 'error': msg}), 400

# --- Notifications ---
@app.route('/api/notifications', methods=['GET'])
@login_required
def api_get_notifications():
    notifs = get_user_notifications(session['user_id'])
    return jsonify({'success': True, 'data': notifs})

@app.route('/api/notifications/<int:notif_id>/read', methods=['POST'])
@login_required
def api_read_notification(notif_id):
    mark_notification_read(notif_id, session['user_id'])
    return jsonify({'success': True})

@app.route('/api/notifications/read-all', methods=['POST'])
@login_required
def api_read_all_notifications():
    mark_all_notifications_read(session['user_id'])
    return jsonify({'success': True})

# --- Export Endpoints ---
@app.route('/api/export/projects.csv', methods=['GET'])
@login_required
def export_projects_csv():
    role = session.get('role')
    user_id = session['user_id']
    if role == 'student':
        projs = list_projects(creator_id=user_id)
    else:
        projs = list_projects()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Title', 'Domain', 'Required Skills', 'Difficulty', 'Type', 'Status', 'Creator', 'Created At'])
    for p in projs:
        writer.writerow([p['id'], p['title'], p['domain'], p['required_skills'], p['difficulty_level'], p['project_type'], p['status'], p.get('creator_name', ''), p['created_at']])

    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment;filename=projects.csv'})

@app.route('/api/export/similarity/<int:project_id>.csv', methods=['GET'])
@login_required
def export_similarity_csv(project_id):
    proj = get_project_by_id(project_id)
    if not proj:
        return jsonify({'success': False, 'error': 'Project not found'}), 404
    similar = find_similar_projects(proj, current_project_id=project_id, top_k=10)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Target Project ID', 'Target Title', 'Similar Project ID', 'Similar Title', 'Creator', 'Status', 'Similarity Score', 'Similarity %', 'Shared Terms'])
    for s in similar:
        keywords = ", ".join(s.get('common_keywords', []))
        writer.writerow([project_id, proj['title'], s['project_id'], s['title'], s.get('creator_name', ''), s['status'], s['similarity_score'], s['similarity_percentage'], keywords])

    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': f'attachment;filename=similarity_project_{project_id}.csv'})

@app.route('/api/export/tasks.csv', methods=['GET'])
@login_required
def export_tasks_csv():
    user_id = session['user_id']
    role = session.get('role')
    if role == 'student':
        projs = list_projects(creator_id=user_id)
    else:
        projs = list_projects()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Task ID', 'Project ID', 'Project Title', 'Task Title', 'Description', 'Assignee', 'Status', 'Progress %', 'Priority', 'Due Date', 'Created At'])

    for p in projs:
        for t in get_project_tasks(p['id']):
            writer.writerow([t['id'], p['id'], p['title'], t['title'], t.get('description', ''), t.get('assignee_name', 'Unassigned'), t['status'], t['progress'], t.get('priority', 'Medium'), t.get('due_date', ''), t['created_at']])

    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment;filename=tasks.csv'})

@app.route('/api/export/admin-stats.csv', methods=['GET'])
@role_required('admin')
def export_admin_stats_csv():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'student'")
    students = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'faculty'")
    faculty = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM projects")
    projects = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM projects WHERE status = 'pending'")
    pending = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM projects WHERE status = 'approved'")
    approved = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM projects WHERE status = 'rejected'")
    rejected = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM project_tasks")
    tasks = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM team_invitations WHERE status = 'pending'")
    invites = cursor.fetchone()[0]
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Metric', 'Value'])
    writer.writerow(['Total Students', students])
    writer.writerow(['Total Faculty', faculty])
    writer.writerow(['Total Projects', projects])
    writer.writerow(['Pending Projects', pending])
    writer.writerow(['Approved Projects', approved])
    writer.writerow(['Rejected Projects', rejected])
    writer.writerow(['Total Tasks', tasks])
    writer.writerow(['Pending Team Invitations', invites])

    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment;filename=admin_stats.csv'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

