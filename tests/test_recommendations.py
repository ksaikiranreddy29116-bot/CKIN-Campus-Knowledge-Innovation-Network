import unittest
import os
from config import TestConfig
from src.database import init_db
from src.auth import register_user
from src.project_service import create_project, approve_project
from src.recommendation_engine import get_recommendations_for_student
from src.team_recommender import recommend_teammates_for_project

class TestRecommendations(unittest.TestCase):
    def setUp(self):
        self.db_path = TestConfig.DATABASE_PATH
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        init_db(self.db_path)

        _, self.s1 = register_user("Student One", "s1@ckin.local", "pass", role="student", extra_data={'skills': 'Python, Flask, Machine Learning'}, db_path=self.db_path)
        _, self.s2 = register_user("Student Two", "s2@ckin.local", "pass", role="student", extra_data={'skills': 'Python, PyTorch, Deep Learning'}, db_path=self.db_path)
        _, self.f1 = register_user("Faculty One", "f1@ckin.local", "pass", role="faculty", db_path=self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_recommendation_flow(self):
        p_id = create_project(
            creator_id=self.s1,
            title="AI Health Monitoring Platform",
            description="Machine Learning system for health monitoring.",
            domain="Artificial Intelligence",
            required_skills="Python, Machine Learning",
            db_path=self.db_path
        )
        approve_project(p_id, self.f1, db_path=self.db_path)

        # Teammate recommendations for s1's project
        teammates = recommend_teammates_for_project(p_id, db_path=self.db_path)
        self.assertTrue(len(teammates) > 0)
        self.assertEqual(teammates[0]['student_id'], self.s2)

        # Student recommendations for s2
        recs = get_recommendations_for_student(self.s2, db_path=self.db_path)
        self.assertTrue(len(recs) > 0)
        self.assertEqual(recs[0]['project_id'], p_id)

if __name__ == '__main__':
    unittest.main()
