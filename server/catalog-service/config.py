import os

class Config:
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///data/books.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'thisisanothersecretkeythatididnotwanttouse'
    CORS_ORIGINS = ["http://localhost:3000"]

    # Upload folder for book covers
    UPLOAD_FOLDER = os.path.join(BASEDIR, 'static', 'cover_images')