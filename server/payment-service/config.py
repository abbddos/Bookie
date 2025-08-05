import os

class Config:
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///data/payments.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'herecomesanotherdreadfulsecretkeythatidonotseemtoditch'
    CORS_ORIGINS = ["http://localhost:3000"] # Adjust if your frontend runs on a different port/domain
