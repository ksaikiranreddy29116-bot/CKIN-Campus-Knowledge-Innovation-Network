import unittest
import os
from config import TestConfig
from src.database import init_db, get_db
from src.auth import register_user

class TestAdmin(unittest.TestCase):
    def setUp(self):
        self.db_path = TestConfig.DATABASE_PATH
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        init_db(self.db_path)

        register_user("Admin User", "admin@ckin.local", "pass", role="admin", db_path=self.db_path)
        register_user("Student User", "student@ckin.local", "pass", role="student", db_path=self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_admin_user_count(self):
        conn = get_db(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'student'")
        s_count = cursor.fetchone()['count']
        conn.close()

        self.assertEqual(s_count, 1)

if __name__ == '__main__':
    unittest.main()
