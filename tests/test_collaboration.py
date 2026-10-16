import unittest
import os
from config import TestConfig
from src.database import init_db
from src.auth import register_user
from src.project_service import create_project, approve_project, create_team_invitation, handle_team_invitation, get_project_members

class TestCollaboration(unittest.TestCase):
    def setUp(self):
        self.db_path = TestConfig.DATABASE_PATH
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        init_db(self.db_path)

        _, self.leader = register_user("Leader", "leader@ckin.local", "pass", role="student", db_path=self.db_path)
        _, self.member = register_user("Member", "member@ckin.local", "pass", role="student", db_path=self.db_path)
        _, self.faculty = register_user("Faculty", "faculty@ckin.local", "pass", role="faculty", db_path=self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_invitation_flow(self):
        pid = create_project(
            creator_id=self.leader,
            title="Team Project",
            description="Testing team invitations.",
            domain="Web Application",
            required_skills="Python, Flask",
            db_path=self.db_path
        )
        approve_project(pid, self.faculty, db_path=self.db_path)

        # Leader invites member
        succ, msg = create_team_invitation(pid, self.leader, self.member, db_path=self.db_path)
        self.assertTrue(succ)

        # Member accepts invitation
        conn = self._get_invitation_id(pid, self.member)
        inv_id = conn
        succ, msg = handle_team_invitation(inv_id, 'accept', self.member, db_path=self.db_path)
        self.assertTrue(succ)

        # Check project membership
        members = get_project_members(pid, db_path=self.db_path)
        m_ids = [m['student_id'] for m in members]
        self.assertIn(self.member, m_ids)

    def _get_invitation_id(self, pid, invitee_id):
        from src.database import get_db
        conn = get_db(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM team_invitations WHERE project_id = ? AND invitee_id = ?", (pid, invitee_id))
        row = cursor.fetchone()
        conn.close()
        return row['id']

if __name__ == '__main__':
    unittest.main()
