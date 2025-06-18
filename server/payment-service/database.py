from flask_sqlalchemy import SQLAlchemy
import os
import sys

db = SQLAlchemy()

def init_db(app):
    db.init_app(app)

def create_db_tables(app):
    with app.app_context():
        db.create_all()
        print("Payment database tables created!")

if __name__ == '__main__':
    from flask import Flask
    from config import Config
    from models import Payment # Import model to ensure it's registered

    print("Attempting to create payment database tables...")
    app = Flask(__name__)
    app.config.from_object(Config)
    init_db(app)

    try:
        create_db_tables(app)
    except Exception as e:
        print(f"Error creating payment database tables: {e}", file=sys.stderr)
        sys.exit(1)