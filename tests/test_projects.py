import unittest
import os
from config import TestConfig
from src.database import init_db
from src.auth import register_user
from src.project_service import create_project, get_project_by_id, list_projects, approve_project, reject_project

class TestProjects(unittest.TestCase):
    def setUp(self):
        self.db_path = TestConfig.DATABASE_PATH
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        init_db(self.db_path)

        _, self.student_id = register_user("Student A", "sA@ckin.local", "pass", role="student", db_path=self.db_path)
        _, self.faculty_id = register_user("Faculty A", "fA@ckin.local", "pass", role="faculty", db_path=self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_create_and_approve_project(self):
        p_id = create_project(
            creator_id=self.student_id,
            title="Test AI System",
            description="Testing project creation and faculty approval workflow.",
            domain="Artificial Intelligence",
            required_skills="Python, ML",
            db_path=self.db_path
        )
        self.assertIsNotNone(p_id)

        p = get_project_by_id(p_id, db_path=self.db_path)
        self.assertEqual(p['status'], 'pending')

        succ, msg = approve_project(p_id, self.faculty_id, db_path=self.db_path)
        self.assertTrue(succ)

        p_approved = get_project_by_id(p_id, db_path=self.db_path)
        self.assertEqual(p_approved['status'], 'approved')

    def test_task_creation_and_progress_update(self):
        from src.project_service import create_project_task, update_task_progress, get_project_tasks
        
        p_id = create_project(
            creator_id=self.student_id,
            title="Task Test Project",
            description="Testing task creation and progress updates.",
            domain="Software Engineering",
            required_skills="Python",
            db_path=self.db_path
        )

        task_id = create_project_task(
            project_id=p_id,
            title="Setup Database",
            description="Create tables and migrations",
            assigned_to=self.student_id,
            due_date="2026-10-31",
            status="pending",
            progress=0,
            db_path=self.db_path
        )
        self.assertIsNotNone(task_id)

        tasks = get_project_tasks(p_id, db_path=self.db_path)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['title'], "Setup Database")
        self.assertEqual(tasks[0]['assigned_to'], self.student_id)

        # Update progress to 75% and status to in_progress
        update_task_progress(task_id, "in_progress", 75, db_path=self.db_path)

        updated_tasks = get_project_tasks(p_id, db_path=self.db_path)
        self.assertEqual(updated_tasks[0]['progress'], 75)
        self.assertEqual(updated_tasks[0]['status'], "in_progress")

    def test_api_task_creation_endpoint(self):
        from app import app
        app.config['TESTING'] = True
        app.config['DATABASE_PATH'] = self.db_path
        
        p_id = create_project(
            creator_id=self.student_id,
            title="CKIN Project 5",
            description="Testing API endpoint task creation",
            domain="Web Development",
            required_skills="Python, Flask",
            db_path=self.db_path
        )

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.student_id
                sess['role'] = 'student'

            # 1. Test valid task creation including title 'implement login pages'
            res = client.post(f'/api/tasks/{p_id}', json={
                'title': 'implement login pages',
                'description': 'Create login UI and auth handlers',
                'assigned_to': self.student_id,
                'due_date': '2026-11-01',
                'status': 'pending',
                'progress': 0,
                'priority': 'High'
            })
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.is_json)
            data = res.get_json()
            self.assertTrue(data.get('success'))
            self.assertIn('task_id', data)

            # Verify persistent saving in DB
            from src.project_service import get_project_tasks
            tasks = get_project_tasks(p_id, db_path=self.db_path)
            self.assertTrue(any(t['title'] == 'implement login pages' for t in tasks))

            # 2. Test invalid input (empty title)
            res_invalid = client.post(f'/api/tasks/{p_id}', json={
                'title': '',
                'description': 'No title task'
            })
            self.assertEqual(res_invalid.status_code, 400)
            self.assertTrue(res_invalid.is_json)
            data_invalid = res_invalid.get_json()
            self.assertFalse(data_invalid.get('success'))
            self.assertEqual(data_invalid.get('error'), 'Task title is required.')

            # 3. Test non-existent project (404)
            res_404 = client.post('/api/tasks/99999', json={
                'title': 'Orphan task'
            })
            self.assertEqual(res_404.status_code, 404)
            self.assertTrue(res_404.is_json)

if __name__ == '__main__':
    unittest.main()

