from flask_sqlalchemy import SQLAlchemy
import os
import sys

# Create a SQLAlchemy database instance
db = SQLAlchemy()

def init_db(app):
    """Initializes the database with the Flask app."""
    db.init_app(app)

def create_db_tables(app):
    """Creates all database tables based on models.py."""
    with app.app_context():
        db.create_all()
        print("Database tables created!")

# This block allows you to run `python database.py` to create the database file and tables
if __name__ == '__main__':
    from flask import Flask
    from config import Config
    # Import User model to ensure it's registered with SQLAlchemy for table creation
    from models import User 

    print("Attempting to create database tables...")
    app = Flask(__name__)
    app.config.from_object(Config)
    init_db(app) # Initialize db instance with this temporary app

    try:
        create_db_tables(app)
    except Exception as e:
        print(f"Error creating database tables: {e}", file=sys.stderr)
        sys.exit(1)
