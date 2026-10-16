import unittest
import os
from config import TestConfig
from src.database import init_db
from src.auth import register_user
from src.project_service import create_project, approve_project
from src.similarity_engine import find_similar_projects

class TestSimilarity(unittest.TestCase):
    def setUp(self):
        self.db_path = TestConfig.DATABASE_PATH
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        init_db(self.db_path)

        _, self.s_id = register_user("Student B", "sB@ckin.local", "pass", role="student", db_path=self.db_path)
        _, self.f_id = register_user("Faculty B", "fB@ckin.local", "pass", role="faculty", db_path=self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_similarity_engine(self):
        p1 = create_project(
            creator_id=self.s_id,
            title="Campus Waste Management using Computer Vision",
            description="Smart camera system detecting waste bins and recycling status.",
            domain="Artificial Intelligence",
            required_skills="Python, PyTorch, OpenCV",
            db_path=self.db_path
        )
        approve_project(p1, self.f_id, db_path=self.db_path)

        new_project = {
            'title': "Automated Garbage and Waste Detection via Computer Vision",
            'description': "Using OpenCV camera feeds to manage campus waste bins.",
            'domain': "Artificial Intelligence",
            'required_skills': "Python, OpenCV",
            'project_type': "Web Application"
        }

        similar = find_similar_projects(new_project, db_path=self.db_path)
        self.assertTrue(len(similar) > 0)
        self.assertGreater(similar[0]['similarity_percentage'], 30.0)

if __name__ == '__main__':
    unittest.main()
