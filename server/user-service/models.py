from database import db
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
# Corrected Import: Use URLSafeTimedSerializer for URL-safe tokens
from itsdangerous import URLSafeTimedSerializer as Serializer, SignatureExpired, BadTimeSignature
from flask import current_app # To access app.config for secret key

class User(db.Model):
    __tablename__ = 'user' # Explicitly name the table

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False) # Store hashed password

    first_name = db.Column(db.String(80), nullable=True)
    last_name = db.Column(db.String(80), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='customer') # e.g., 'admin', 'store', 'sales', 'customer'
    profile_pic = db.Column(db.String(255), nullable=True) # URL or path to profile picture
    is_verified = db.Column(db.Boolean, default=False, nullable=False) # NEW FIELD: For email verification status

    created_at = db.Column(db.DateTime, default=datetime.datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    def __init__(self, username, email, password, first_name=None, last_name=None, role='sales', profile_pic=None):
        self.username = username
        self.email = email
        self.set_password(password) # Hash password on creation
        self.first_name = first_name
        self.last_name = last_name
        self.role = role
        self.profile_pic = profile_pic
        # is_verified defaults to False

    def set_password(self, password):
        """Hashes the password and stores it."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Checks if the provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    def get_reset_token(self, expires_sec=1800):
        """
        Generates a URL-safe, time-limited token for password reset.
        Uses the app's SECRET_KEY for signing.
        """
        s = Serializer(current_app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        """
        Verifies a password reset token.
        Returns the User object if the token is valid and not expired, otherwise None.
        """
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except (SignatureExpired, BadTimeSignature):
            # Token is expired or invalid
            return None
        except Exception:
            # Catch any other unexpected errors during token loading
            return None
        return User.query.get(user_id)

    def to_dict(self):
        """Converts user object to a dictionary for JSON serialization, excluding password hash."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role,
            'profile_pic': self.profile_pic,
            'is_verified': self.is_verified, # Include verification status
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<User {self.username}>'