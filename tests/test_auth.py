import unittest
import os
from config import TestConfig
from src.database import init_db
from src.auth import register_user, authenticate_user, get_user_by_id

class TestAuth(unittest.TestCase):
    def setUp(self):
        self.db_path = TestConfig.DATABASE_PATH
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        init_db(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_student_registration_and_login(self):
        success, uid = register_user("Test Student", "teststudent@ckin.local", "pass123", role="student", db_path=self.db_path)
        self.assertTrue(success)
        self.assertIsInstance(uid, int)

        user, msg = authenticate_user("teststudent@ckin.local", "pass123", db_path=self.db_path)
        self.assertIsNotNone(user)
        self.assertEqual(user['role'], 'student')

        profile = get_user_by_id(uid, db_path=self.db_path)
        self.assertEqual(profile['name'], "Test Student")
        self.assertIn('profile', profile)

    def test_invalid_login(self):
        user, msg = authenticate_user("nonexistent@ckin.local", "wrong", db_path=self.db_path)
        self.assertIsNone(user)

if __name__ == '__main__':
    unittest.main()
