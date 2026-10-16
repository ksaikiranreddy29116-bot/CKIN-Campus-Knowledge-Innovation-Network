from src.database import get_db
from src.activity_service import log_activity
from src.notification_service import create_notification

def create_project(creator_id, title, description, domain, required_skills,
                   difficulty_level='Medium', project_type='Web Application',
                   weekly_commitment=10, team_size=4, expected_duration='3 Months', db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO projects (
            creator_id, title, description, domain, required_skills,
            difficulty_level, project_type, weekly_commitment, team_size, expected_duration, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
    """, (
        creator_id, title, description, domain, required_skills,
        difficulty_level, project_type, weekly_commitment, team_size, expected_duration
    ))

    project_id = cursor.lastrowid

    # Automatically add creator as Leader in project_members
    cursor.execute("""
        INSERT INTO project_members (project_id, student_id, role_in_project)
        VALUES (?, ?, 'Leader')
    """, (project_id, creator_id))

    conn.commit()
    conn.close()

    log_activity(creator_id, "CREATE_PROJECT", "project", project_id, f"Created project '{title}'", db_path=db_path)

    # Notify faculty members about new submission
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE role = 'faculty'")
    faculty_users = cursor.fetchall()
    conn.close()

    for f in faculty_users:
        create_notification(f['id'], f"New project submission awaiting approval: '{title}'", "approval_request", project_id, db_path=db_path)

    return project_id

def get_project_by_id(project_id, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, u.name as creator_name, u.email as creator_email
        FROM projects p
        JOIN users u ON p.creator_id = u.id
        WHERE p.id = ?
    """, (project_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)

def list_projects(status=None, domain=None, project_type=None, search=None, creator_id=None, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()

    query = """
        SELECT p.*, u.name as creator_name
        FROM projects p
        JOIN users u ON p.creator_id = u.id
        WHERE 1=1
    """
    params = []

    if status:
        query += " AND p.status = ?"
        params.append(status)
    if domain:
        query += " AND p.domain LIKE ?"
        params.append(f"%{domain}%")
    if project_type:
        query += " AND p.project_type = ?"
        params.append(project_type)
    if creator_id:
        query += " AND p.creator_id = ?"
        params.append(creator_id)
    if search:
        query += " AND (p.title LIKE ? OR p.description LIKE ? OR p.required_skills LIKE ? OR p.domain LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term, term])

    query += " ORDER BY p.created_at DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def approve_project(project_id, faculty_user_id, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT creator_id, title, status FROM projects WHERE id = ?", (project_id,))
    project = cursor.fetchone()
    if not project:
        conn.close()
        return False, "Project not found."

    cursor.execute("UPDATE projects SET status = 'approved', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()

    log_activity(faculty_user_id, "APPROVE_PROJECT", "project", project_id, f"Approved project '{project['title']}'", db_path=db_path)
    create_notification(project['creator_id'], f"Your project '{project['title']}' has been APPROVED by faculty!", "project_approval", project_id, db_path=db_path)

    return True, "Project approved successfully."

def reject_project(project_id, faculty_user_id, rejection_reason="", db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT creator_id, title, status FROM projects WHERE id = ?", (project_id,))
    project = cursor.fetchone()
    if not project:
        conn.close()
        return False, "Project not found."

    cursor.execute("""
        UPDATE projects
        SET status = 'rejected', rejection_reason = ?, reviewer_id = ?, reviewed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (rejection_reason, faculty_user_id, project_id))
    conn.commit()
    conn.close()

    log_activity(faculty_user_id, "REJECT_PROJECT", "project", project_id, f"Rejected project '{project['title']}'", db_path=db_path)
    create_notification(project['creator_id'], f"Your project '{project['title']}' has been REJECTED by faculty. Reason: {rejection_reason or 'None provided.'}", "project_rejection", project_id, db_path=db_path)

    return True, "Project rejected successfully."

def cancel_join_request(request_id, student_id, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM join_requests WHERE id = ? AND student_id = ?", (request_id, student_id))
    req = cursor.fetchone()
    if not req:
        conn.close()
        return False, "Join request not found or unauthorized."
    cursor.execute("DELETE FROM join_requests WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()
    return True, "Join request cancelled."

def cancel_team_invitation(invitation_id, current_user_id, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM team_invitations WHERE id = ? AND (inviter_id = ? OR invitee_id = ?)", (invitation_id, current_user_id, current_user_id))
    inv = cursor.fetchone()
    if not inv:
        conn.close()
        return False, "Invitation not found or unauthorized."
    cursor.execute("UPDATE team_invitations SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (invitation_id,))
    conn.commit()
    conn.close()
    return True, "Invitation cancelled."

def create_project_task(project_id, title, description="", assigned_to=None, due_date="", status="pending", progress=0, priority="Medium", db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    progress = max(0, min(100, int(progress)))
    if status not in ['pending', 'in_progress', 'completed']:
        status = 'pending'
    if priority not in ['Low', 'Medium', 'High']:
        priority = 'Medium'
    cursor.execute("""
        INSERT INTO project_tasks (project_id, title, description, assigned_to, due_date, status, progress, priority)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (project_id, title, description, assigned_to, due_date, status, progress, priority))
    task_id = cursor.lastrowid
    conn.commit()

    # Notify assignee if assigned
    if assigned_to:
        create_notification(assigned_to, f"You have been assigned a task: '{title}'", "task_assignment", project_id, db_path=db_path)

    conn.close()
    return task_id

def update_task_details(task_id, title, description, assigned_to, due_date, status, progress, priority="Medium", db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    progress = max(0, min(100, int(progress)))
    if status not in ['pending', 'in_progress', 'completed']:
        status = 'pending'
    if priority not in ['Low', 'Medium', 'High']:
        priority = 'Medium'

    cursor.execute("SELECT project_id, assigned_to, title FROM project_tasks WHERE id = ?", (task_id,))
    old_task = cursor.fetchone()
    if not old_task:
        conn.close()
        return False, "Task not found."

    cursor.execute("""
        UPDATE project_tasks
        SET title = ?, description = ?, assigned_to = ?, due_date = ?, status = ?, progress = ?, priority = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (title, description, assigned_to, due_date, status, progress, priority, task_id))
    conn.commit()

    if assigned_to and assigned_to != old_task['assigned_to']:
        create_notification(assigned_to, f"Task '{title}' has been assigned to you.", "task_assignment", old_task['project_id'], db_path=db_path)

    conn.close()
    return True, "Task updated successfully."

def update_task_progress(task_id, status, progress, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    progress = max(0, min(100, int(progress)))
    if status not in ['pending', 'in_progress', 'completed']:
        status = 'pending'
    cursor.execute("""
        UPDATE project_tasks
        SET status = ?, progress = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (status, progress, task_id))
    conn.commit()
    conn.close()

def delete_project_task(task_id, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM project_tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return True, "Task deleted successfully."

def get_project_tasks(project_id, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pt.*, u.name as assignee_name
        FROM project_tasks pt
        LEFT JOIN users u ON pt.assigned_to = u.id
        WHERE pt.project_id = ?
        ORDER BY pt.created_at DESC
    """, (project_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --- Comments ---
def create_project_comment(project_id, author_id, comment_text, db_path=None):
    if not comment_text or not comment_text.strip():
        return False, "Comment cannot be empty."
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO project_comments (project_id, author_id, comment_text)
        VALUES (?, ?, ?)
    """, (project_id, author_id, comment_text.strip()))
    comment_id = cursor.lastrowid
    conn.commit()

    cursor.execute("SELECT title, creator_id FROM projects WHERE id = ?", (project_id,))
    proj = cursor.fetchone()
    conn.close()

    if proj and proj['creator_id'] != author_id:
        create_notification(proj['creator_id'], f"New comment on your project '{proj['title']}'", "comment", project_id, db_path=db_path)

    return True, comment_id

def get_project_comments(project_id, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pc.*, u.name as author_name, u.role as author_role
        FROM project_comments pc
        JOIN users u ON pc.author_id = u.id
        WHERE pc.project_id = ?
        ORDER BY pc.created_at ASC
    """, (project_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_project_comment(comment_id, user_id, user_role, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT author_id FROM project_comments WHERE id = ?", (comment_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False, "Comment not found."
    if row['author_id'] != user_id and user_role not in ['faculty', 'admin']:
        conn.close()
        return False, "Unauthorized to delete this comment."
    cursor.execute("DELETE FROM project_comments WHERE id = ?", (comment_id,))
    conn.commit()
    conn.close()
    return True, "Comment deleted."

# --- Resources ---
def create_project_resource(project_id, uploader_id, title, description, resource_url, db_path=None):
    if not title or not resource_url:
        return False, "Resource title and URL are required."
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO project_resources (project_id, uploader_id, title, description, resource_url)
        VALUES (?, ?, ?, ?, ?)
    """, (project_id, uploader_id, title.strip(), description.strip(), resource_url.strip()))
    res_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return True, res_id

def get_project_resources(project_id, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pr.*, u.name as uploader_name
        FROM project_resources pr
        JOIN users u ON pr.uploader_id = u.id
        WHERE pr.project_id = ?
        ORDER BY pr.created_at DESC
    """, (project_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_project_resource(resource_id, user_id, user_role, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT uploader_id FROM project_resources WHERE id = ?", (resource_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False, "Resource not found."
    if row['uploader_id'] != user_id and user_role not in ['faculty', 'admin']:
        conn.close()
        return False, "Unauthorized to delete this resource."
    cursor.execute("DELETE FROM project_resources WHERE id = ?", (resource_id,))
    conn.commit()
    conn.close()
    return True, "Resource deleted."

# --- Milestones ---
def create_project_milestone(project_id, title, description="", due_date="", db_path=None):
    if not title or not title.strip():
        return False, "Milestone title is required."
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO project_milestones (project_id, title, description, due_date, status)
        VALUES (?, ?, ?, ?, 'pending')
    """, (project_id, title.strip(), description.strip(), due_date.strip()))
    ms_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return True, ms_id

def get_project_milestones(project_id, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM project_milestones
        WHERE project_id = ?
        ORDER BY created_at ASC
    """, (project_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_milestone_status(milestone_id, status, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    if status == 'completed':
        cursor.execute("UPDATE project_milestones SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = ?", (milestone_id,))
    else:
        cursor.execute("UPDATE project_milestones SET status = 'pending', completed_at = NULL WHERE id = ?", (milestone_id,))
    conn.commit()
    conn.close()
    return True, "Milestone status updated."

def delete_project_milestone(milestone_id, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM project_milestones WHERE id = ?", (milestone_id,))
    conn.commit()
    conn.close()
    return True, "Milestone deleted."


def get_project_members(project_id, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pm.*, u.name, u.email, sp.year, sp.cgpa, sp.skills
        FROM project_members pm
        JOIN users u ON pm.student_id = u.id
        LEFT JOIN student_profiles sp ON u.id = sp.user_id
        WHERE pm.project_id = ?
        ORDER BY pm.joined_at ASC
    """, (project_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_join_request(project_id, student_id, message="", db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT creator_id, title, status, team_size FROM projects WHERE id = ?", (project_id,))
    project = cursor.fetchone()
    if not project:
        conn.close()
        return False, "Project not found."

    if project['status'] != 'approved':
        conn.close()
        return False, "Can only request to join approved projects."

    # Check if already member
    cursor.execute("SELECT id FROM project_members WHERE project_id = ? AND student_id = ?", (project_id, student_id))
    if cursor.fetchone():
        conn.close()
        return False, "You are already a member of this project."

    # Check capacity
    cursor.execute("SELECT COUNT(*) as count FROM project_members WHERE project_id = ?", (project_id,))
    member_count = cursor.fetchone()['count']
    if member_count >= project['team_size']:
        conn.close()
        return False, "Project team is already full."

    try:
        cursor.execute("""
            INSERT INTO join_requests (project_id, student_id, message, status)
            VALUES (?, ?, ?, 'pending')
        """, (project_id, student_id, message))
        req_id = cursor.lastrowid
        conn.commit()
        conn.close()

        log_activity(student_id, "JOIN_REQUEST", "project", project_id, f"Requested to join '{project['title']}'", db_path=db_path)
        create_notification(project['creator_id'], f"A student requested to join your project '{project['title']}'", "join_request", project_id, db_path=db_path)

        return True, "Join request submitted successfully."
    except Exception as e:
        conn.close()
        return False, "Join request already exists or invalid."

def handle_join_request(request_id, action, current_user_id, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT jr.*, p.creator_id, p.title as project_title, p.team_size
        FROM join_requests jr
        JOIN projects p ON jr.project_id = p.id
        WHERE jr.id = ?
    """, (request_id,))
    req = cursor.fetchone()
    if not req:
        conn.close()
        return False, "Join request not found."

    if req['creator_id'] != current_user_id:
        conn.close()
        return False, "Unauthorized to manage this join request."

    if action == 'accept':
        # Check capacity
        cursor.execute("SELECT COUNT(*) as count FROM project_members WHERE project_id = ?", (req['project_id'],))
        member_count = cursor.fetchone()['count']
        if member_count >= req['team_size']:
            conn.close()
            return False, "Project team is full."

        cursor.execute("UPDATE join_requests SET status = 'accepted', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (request_id,))
        cursor.execute("""
            INSERT OR IGNORE INTO project_members (project_id, student_id, role_in_project)
            VALUES (?, ?, 'Member')
        """, (req['project_id'], req['student_id']))
        conn.commit()
        conn.close()

        log_activity(current_user_id, "ACCEPT_JOIN_REQUEST", "project", req['project_id'], f"Accepted join request for '{req['project_title']}'", db_path=db_path)
        create_notification(req['student_id'], f"Your request to join '{req['project_title']}' was ACCEPTED!", "join_accepted", req['project_id'], db_path=db_path)
        return True, "Join request accepted."

    elif action == 'reject':
        cursor.execute("UPDATE join_requests SET status = 'rejected', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (request_id,))
        conn.commit()
        conn.close()

        log_activity(current_user_id, "REJECT_JOIN_REQUEST", "project", req['project_id'], f"Rejected join request for '{req['project_title']}'", db_path=db_path)
        create_notification(req['student_id'], f"Your request to join '{req['project_title']}' was rejected.", "join_rejected", req['project_id'], db_path=db_path)
        return True, "Join request rejected."

    conn.close()
    return False, "Invalid action."

def create_team_invitation(project_id, inviter_id, invitee_id, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT creator_id, title FROM projects WHERE id = ?", (project_id,))
    project = cursor.fetchone()
    if not project:
        conn.close()
        return False, "Project not found."

    # Verify inviter is leader or member
    cursor.execute("SELECT id FROM project_members WHERE project_id = ? AND student_id = ?", (project_id, inviter_id))
    if not cursor.fetchone():
        conn.close()
        return False, "Only project team members can send invitations."

    # Verify invitee is active student
    cursor.execute("SELECT id, name FROM users WHERE id = ? AND role = 'student' AND is_active = 1", (invitee_id,))
    invitee = cursor.fetchone()
    if not invitee:
        conn.close()
        return False, "Invitee is not a valid student."

    # Check if already member
    cursor.execute("SELECT id FROM project_members WHERE project_id = ? AND student_id = ?", (project_id, invitee_id))
    if cursor.fetchone():
        conn.close()
        return False, "Student is already a team member."

    cursor.execute("""
        INSERT INTO team_invitations (project_id, inviter_id, invitee_id, status)
        VALUES (?, ?, ?, 'pending')
    """, (project_id, inviter_id, invitee_id))
    inv_id = cursor.lastrowid
    conn.commit()
    conn.close()

    log_activity(inviter_id, "INVITE_STUDENT", "project", project_id, f"Invited student {invitee['name']} to project '{project['title']}'", db_path=db_path)
    create_notification(invitee_id, f"You have been invited to join project '{project['title']}'!", "team_invitation", project_id, db_path=db_path)

    return True, "Invitation sent successfully."

def handle_team_invitation(invitation_id, action, invitee_id, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ti.*, p.title as project_title, p.team_size
        FROM team_invitations ti
        JOIN projects p ON ti.project_id = p.id
        WHERE ti.id = ?
    """, (invitation_id,))
    inv = cursor.fetchone()
    if not inv:
        conn.close()
        return False, "Invitation not found."

    if inv['invitee_id'] != invitee_id:
        conn.close()
        return False, "Unauthorized to respond to this invitation."

    if action == 'accept':
        # Check capacity
        cursor.execute("SELECT COUNT(*) as count FROM project_members WHERE project_id = ?", (inv['project_id'],))
        member_count = cursor.fetchone()['count']
        if member_count >= inv['team_size']:
            conn.close()
            return False, "Project team is full."

        cursor.execute("UPDATE team_invitations SET status = 'accepted', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (invitation_id,))
        cursor.execute("""
            INSERT OR IGNORE INTO project_members (project_id, student_id, role_in_project)
            VALUES (?, ?, 'Member')
        """, (inv['project_id'], invitee_id))
        conn.commit()
        conn.close()

        log_activity(invitee_id, "ACCEPT_INVITATION", "project", inv['project_id'], f"Accepted invitation to '{inv['project_title']}'", db_path=db_path)
        create_notification(inv['inviter_id'], f"Student accepted your invitation to join '{inv['project_title']}'!", "invitation_accepted", inv['project_id'], db_path=db_path)
        return True, "Invitation accepted!"

    elif action == 'decline':
        cursor.execute("UPDATE team_invitations SET status = 'declined', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (invitation_id,))
        conn.commit()
        conn.close()

        log_activity(invitee_id, "DECLINE_INVITATION", "project", inv['project_id'], f"Declined invitation to '{inv['project_title']}'", db_path=db_path)
        create_notification(inv['inviter_id'], f"Student declined your invitation to join '{inv['project_title']}'.", "invitation_declined", inv['project_id'], db_path=db_path)
        return True, "Invitation declined."

    conn.close()
    return False, "Invalid action."

def get_user_invitations(user_id, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ti.*, p.title as project_title, u.name as inviter_name
        FROM team_invitations ti
        JOIN projects p ON ti.project_id = p.id
        JOIN users u ON ti.inviter_id = u.id
        WHERE ti.invitee_id = ?
        ORDER BY ti.created_at DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user_join_requests(user_id, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT jr.*, p.title as project_title
        FROM join_requests jr
        JOIN projects p ON jr.project_id = p.id
        WHERE jr.student_id = ?
        ORDER BY jr.created_at DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_project_join_requests(project_id, db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT jr.*, u.name as student_name, u.email as student_email, sp.year, sp.cgpa, sp.skills
        FROM join_requests jr
        JOIN users u ON jr.student_id = u.id
        LEFT JOIN student_profiles sp ON u.id = sp.user_id
        WHERE jr.project_id = ?
        ORDER BY jr.created_at DESC
    """, (project_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

