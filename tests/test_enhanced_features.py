import unittest
import os
import tempfile
from app import app
from src.database import init_db, get_db
from src.auth import register_user, authenticate_user
from src.project_service import (
    create_project, approve_project, reject_project,
    create_project_task, update_task_details, delete_project_task, get_project_tasks,
    create_team_invitation, handle_team_invitation, cancel_team_invitation,
    create_join_request, cancel_join_request,
    create_project_comment, get_project_comments, delete_project_comment,
    create_project_resource, get_project_resources, delete_project_resource,
    create_project_milestone, get_project_milestones, update_milestone_status, delete_project_milestone
)

class TestEnhancedFeatures(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        app.config['TESTING'] = True
        app.config['DATABASE_PATH'] = self.db_path
        self.app_client = app.test_client()

        with app.app_context():
            init_db(self.db_path)

        # Setup test users
        register_user("Test Admin", "admin@test.com", "pass123", "admin", db_path=self.db_path)
        register_user("Test Faculty", "faculty@test.com", "pass123", "faculty", extra_data={"department": "CS"}, db_path=self.db_path)
        register_user("Student One", "student1@test.com", "pass123", "student", extra_data={"year": 3, "skills": "Python, Flask"}, db_path=self.db_path)
        register_user("Student Two", "student2@test.com", "pass123", "student", extra_data={"year": 2, "skills": "JavaScript, React"}, db_path=self.db_path)

        conn = get_db(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, email FROM users")
        self.users = {row['email']: row['id'] for row in cursor.fetchall()}
        conn.close()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_task_management_full_lifecycle(self):
        # Create Project
        p_id = create_project(self.users['student1@test.com'], "Task Test Project", "Desc", "Web", "Python", db_path=self.db_path)

        # Create Task with priority
        t_id = create_project_task(p_id, "Backend API", "Create Flask REST endpoints", assigned_to=self.users['student1@test.com'], priority="High", db_path=self.db_path)
        self.assertIsNotNone(t_id)

        # Retrieve Tasks
        tasks = get_project_tasks(p_id, db_path=self.db_path)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['priority'], "High")

        # Update Task Details
        succ, msg = update_task_details(t_id, "Updated Backend API", "Updated Desc", self.users['student2@test.com'], "2026-12-31", "in_progress", 50, "Low", db_path=self.db_path)
        self.assertTrue(succ)

        tasks_updated = get_project_tasks(p_id, db_path=self.db_path)
        self.assertEqual(tasks_updated[0]['title'], "Updated Backend API")
        self.assertEqual(tasks_updated[0]['priority'], "Low")
        self.assertEqual(tasks_updated[0]['progress'], 50)

        # Delete Task
        del_succ, del_msg = delete_project_task(t_id, db_path=self.db_path)
        self.assertTrue(del_succ)
        self.assertEqual(len(get_project_tasks(p_id, db_path=self.db_path)), 0)

    def test_workspace_collaboration_features(self):
        p_id = create_project(self.users['student1@test.com'], "Workspace Project", "Desc", "AI", "Python", db_path=self.db_path)

        # Test Comments
        c_succ, c_id = create_project_comment(p_id, self.users['student1@test.com'], "Initial kickoff comment", db_path=self.db_path)
        self.assertTrue(c_succ)
        comments = get_project_comments(p_id, db_path=self.db_path)
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0]['comment_text'], "Initial kickoff comment")

        d_succ, _ = delete_project_comment(c_id, self.users['student1@test.com'], 'student', db_path=self.db_path)
        self.assertTrue(d_succ)

        # Test Resources
        r_succ, r_id = create_project_resource(p_id, self.users['student1@test.com'], "GitHub Repo", "Source code link", "https://github.com/example/repo", db_path=self.db_path)
        self.assertTrue(r_succ)
        resources = get_project_resources(p_id, db_path=self.db_path)
        self.assertEqual(len(resources), 1)
        self.assertEqual(resources[0]['resource_url'], "https://github.com/example/repo")

        rd_succ, _ = delete_project_resource(r_id, self.users['student1@test.com'], 'student', db_path=self.db_path)
        self.assertTrue(rd_succ)

        # Test Milestones
        m_succ, m_id = create_project_milestone(p_id, "MVP Release", "Deliver working prototype", "2026-11-01", db_path=self.db_path)
        self.assertTrue(m_succ)
        milestones = get_project_milestones(p_id, db_path=self.db_path)
        self.assertEqual(len(milestones), 1)
        self.assertEqual(milestones[0]['status'], 'pending')

        update_milestone_status(m_id, 'completed', db_path=self.db_path)
        ms_updated = get_project_milestones(p_id, db_path=self.db_path)
        self.assertEqual(ms_updated[0]['status'], 'completed')

        md_succ, _ = delete_project_milestone(m_id, db_path=self.db_path)
        self.assertTrue(md_succ)

    def test_cancellation_and_faculty_rejection_reason(self):
        p_id = create_project(self.users['student1@test.com'], "Review Test Project", "Desc", "Cyber", "Security", db_path=self.db_path)

        # Test Faculty Rejection Reason
        rej_succ, _ = reject_project(p_id, self.users['faculty@test.com'], rejection_reason="Scope too broad.", db_path=self.db_path)
        self.assertTrue(rej_succ)

        conn = get_db(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT status, rejection_reason FROM projects WHERE id = ?", (p_id,))
        p_row = cursor.fetchone()
        conn.close()
        self.assertEqual(p_row['status'], 'rejected')
        self.assertEqual(p_row['rejection_reason'], "Scope too broad.")

        # Test Join Request Cancel
        p_approved = create_project(self.users['student1@test.com'], "Approved Project", "Desc", "Web", "HTML", db_path=self.db_path)
        approve_project(p_approved, self.users['faculty@test.com'], db_path=self.db_path)

        jr_succ, _ = create_join_request(p_approved, self.users['student2@test.com'], "Join me", db_path=self.db_path)
        self.assertTrue(jr_succ)

        conn = get_db(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM join_requests WHERE project_id = ? AND student_id = ?", (p_approved, self.users['student2@test.com']))
        jr_id = cursor.fetchone()['id']
        conn.close()

        cancel_succ, _ = cancel_join_request(jr_id, self.users['student2@test.com'], db_path=self.db_path)
        self.assertTrue(cancel_succ)

if __name__ == '__main__':
    unittest.main()
