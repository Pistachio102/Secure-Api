import os

SECRET_KEY = 'top-secret'
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://postgres:123@localhost/secureApi')
SQLALCHEMY_TRACK_MODIFICATIONS = False
