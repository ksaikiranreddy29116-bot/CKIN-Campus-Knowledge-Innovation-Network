import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ckin-secret-key-dev-2026-secure')
    DATABASE_PATH = os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, 'database', 'ckin.db'))
    MODELS_DIR = os.path.join(BASE_DIR, 'models')
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    TESTING = False
    DEBUG = True

class TestConfig(Config):
    TESTING = True
    DEBUG = False
    DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'ckin_test.db')
