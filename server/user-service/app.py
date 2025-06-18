from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from models import User, db # Import User model and db instance
from database import init_db # Import init_db function
from config import Config # Import configuration
import string
import random
import os
from werkzeug.utils import secure_filename
import uuid
from PIL import Image # For image processing
# Corrected Import: For password reset tokens and verification
from itsdangerous import URLSafeTimedSerializer as Serializer, SignatureExpired, BadTimeSignature 
import datetime # For timestamps

app = Flask(__name__)
app.config.from_object(Config)
init_db(app)

# Constants for file uploads and image processing
ALLOWED_ROLES = ['admin', 'store', 'sales', 'customer']
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
UPLOAD_FOLDER = Config.UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True) # Ensure upload directory exists

TARGET_PROFILE_PIC_SIZE = (200, 200) # Max width, max height

def allowed_file(filename):
    """Checks if a file's extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



def process_profile_picture(filepath):
    """
    Resizes an image saved at filepath to TARGET_PROFILE_PIC_SIZE.
    Saves the resized image, overwriting the original.
    Returns the original filepath (as the file is processed in place).
    """
    try:
        img = Image.open(filepath)
        img.thumbnail(TARGET_PROFILE_PIC_SIZE, Image.Resampling.LANCZOS) 
        img.save(filepath) 
        return filepath
    except Exception as e:
        app.logger.error(f"Error processing image {filepath}: {e}")
        return filepath # Return original path, indicating processing failed.
    


def generate_random_password(length=12):
    """Generates a random alphanumeric password."""
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(characters) for i in range(length))
    return password 


CORS(app, resources={r"/*": {"origins": Config.CORS_ORIGINS}})


@app.route('/')
def home():
    """Root endpoint for the User Service."""
    return jsonify({"message": "User Service is running!", "status": "OK"})



#-- Core CRUD API functions --#
@app.route('/users', methods=['POST'])
def create_user():
    """
    Creates a new user.
    Requires: 'username', 'email'.
    Optional: 'password', 'first_name', 'last_name', 'role', 'profile_pic' (file upload or URL).
    A random password will be generated if not provided.
    Returns: JSON of the created user (excluding password_hash) and the generated password (if any).
    """
    data = request.get_json(silent=True) # Try to get JSON data first
    if data is None:
        data = request.form # Fallback to form data

    username = data.get('username')
    email = data.get('email')
    password = data.get('password') # Allow password to be provided directly for registration

    if not username or not email:
        return jsonify({"error": "Missing username or email"}), 400
    
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    role = data.get('role', 'customer') # Default role

    profile_pic_path = None
    if 'profile_pic' in request.files and request.files['profile_pic'].filename != '':
        file = request.files['profile_pic']
        if file and allowed_file(file.filename):
            filename_orig = secure_filename(file.filename)
            unique_filename = str(uuid.uuid4()) + '_' + filename_orig
            file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            try:
                file.save(file_path)
                processed_file_path = process_profile_picture(file_path)
                profile_pic_path = f"/static/profile_pics/{os.path.basename(processed_file_path)}"
            except Exception as e:
                app.logger.error(f"Error during profile picture save/process for create_user: {e}")
                return jsonify({"error": "Failed to save or process profile picture"}), 500
        else:
            return jsonify({"error": "Invalid file type for profile picture"}), 400
    elif 'profile_pic' in data: # Allows setting by URL directly or clearing it
        profile_pic_path = data.get('profile_pic')

    if role not in ALLOWED_ROLES:
        return jsonify({"error": f"Invalid role. Allowed roles are: {', '.join(ALLOWED_ROLES)}"}), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 409
    
    try:
        new_user = User(
            username=username,
            email=email,
            password=password, # Use provided password or generated one
            first_name=first_name,
            last_name=last_name,
            role=role,
            profile_pic=profile_pic_path
        )
        db.session.add(new_user)
        db.session.commit()

        user_dict = new_user.to_dict()
        # Only return generated password if it was indeed generated (not provided by user)
        if not data.get('password'):
            user_dict['generated_password'] = password

        return jsonify(user_dict), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creating user: {e}")
        return jsonify({"error": "Failed to create user", "details": str(e)}), 500
    

    
@app.route('/users', methods=['GET'])
def get_all_users():
    """
    Retrieves all users.
    Returns: JSON list of all users (excluding password_hash).
    """
    users = User.query.all()
    return jsonify([user.to_dict() for user in users]), 200


@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """
    Retrieves a single user by ID.
    Returns: JSON of the user (excluding password_hash) or 404 if not found.
    """
    user = User.query.get(user_id)
    if user:
        return jsonify(user.to_dict()), 200
    return jsonify({"error": "User not found"}), 404


@app.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """
    Updates an existing user's general information (excluding password).
    Allows updating username, email, first_name, last_name, role, and profile_pic (file upload or URL).
    Password changes must be done via the dedicated /users/<id>/password endpoint.
    Returns: JSON of the updated user (excluding password_hash) or error.
    """
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json(silent=True)
    if data is None:
        data = request.form
    
    if not data and not request.files:
        return jsonify({"error": "No data or files provided for update"}), 400

    try:
        if 'username' in data:
            if User.query.filter(User.username == data['username'], User.id != user_id).first():
                return jsonify({"error": "Username already taken"}), 409
            user.username = data['username']
        if 'email' in data:
            if User.query.filter(User.email == data['email'], User.id != user_id).first():
                return jsonify({"error": "Email already taken"}), 409
            user.email = data['email']
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'role' in data:
            new_role = data['role']
            if new_role not in ALLOWED_ROLES:
                return jsonify({"error": f"Invalid role. Allowed roles are: {', '.join(ALLOWED_ROLES)}"}), 400
            user.role = new_role

        if 'profile_pic' in request.files and request.files['profile_pic'].filename != '':
            file = request.files['profile_pic']
            if file and allowed_file(file.filename):
                filename_orig = secure_filename(file.filename)
                unique_filename = str(uuid.uuid4()) + '_' + filename_orig
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                try:
                    # Delete old profile picture if it exists
                    if user.profile_pic and \
                       os.path.exists(os.path.join(app.root_path, user.profile_pic.lstrip('/'))):
                        os.remove(os.path.join(app.root_path, user.profile_pic.lstrip('/')))

                    file.save(file_path)
                    processed_file_path = process_profile_picture(file_path)
                    user.profile_pic = f"/static/profile_pics/{os.path.basename(processed_file_path)}"
                except Exception as e:
                    app.logger.error(f"Error during profile picture save/process for update_user: {e}")
                    return jsonify({"error": "Failed to save or process profile picture"}), 500
            else:
                return jsonify({"error": "Invalid file type for profile picture"}), 400
        elif 'profile_pic' in data: # Allows setting by URL directly or clearing it
            user.profile_pic = data.get('profile_pic')

        db.session.commit()
        return jsonify(user.to_dict()), 200
    except (ValueError, TypeError):
        db.session.rollback()
        return jsonify({"error": "Invalid type for data fields"}), 400
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating user {user_id}: {e}")
        return jsonify({"error": "Failed to update user", "details": str(e)}), 500
    


@app.route('/users/<int:user_id>/password', methods=['PUT'])
def change_user_password(user_id):
    """
    Changes a user's password.
    Requires: JSON body with 'current_password' and 'new_password'.
    Returns: Success message or error.
    """
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    if not data or not all(key in data for key in ['current_password', 'new_password']):
        return jsonify({"error": "Missing current_password or new_password"}), 400

    current_password = data['current_password']
    new_password = data['new_password']

    if not user.check_password(current_password):
        return jsonify({"error": "Incorrect current password"}), 401

    try:
        user.set_password(new_password)
        user.updated_at = datetime.datetime.now() # Update timestamp
        db.session.commit()
        return jsonify({"message": "Password updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error changing password for user {user_id}: {e}")
        return jsonify({"error": "Failed to change password", "details": str(e)}), 500
    

@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """
    Deletes a user by ID.
    Returns: Success message or 404 if not found.
    """
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    try:
        # Delete associated profile picture file if it exists
        if user.profile_pic and \
           os.path.exists(os.path.join(app.root_path, user.profile_pic.lstrip('/'))):
            os.remove(os.path.join(app.root_path, user.profile_pic.lstrip('/')))

        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": f"User {user_id} deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting user {user_id}: {e}")
        return jsonify({"error": "Failed to delete user", "details": str(e)}), 500
    

#-- Additional API Functions --#
@app.route('/login', methods=['POST'])
def login_user_service():
    """
    Authenticates a user by username/email and password.
    Returns user data if credentials are valid, otherwise an error.
    """
    data = request.get_json()
    username_or_email = data.get('username_or_email')
    password = data.get('password')

    if not username_or_email or not password:
        return jsonify({"error": "Missing username/email or password"}), 400

    # Try to find user by username or email
    user = User.query.filter((User.username == username_or_email) | (User.email == username_or_email)).first()

    if user and user.check_password(password):
        # Return user data (excluding password hash)
        return jsonify(user.to_dict()), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401
    

@app.route('/request-password-reset', methods=['POST'])
def request_password_reset():
    """
    Handles a request to initiate a password reset.
    Receives an email, generates a reset token if the user exists,
    and returns a generic success message for security reasons.
    (In a real app, this would also trigger an email sending process.)
    """
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({"error": "Email is required"}), 400

    user = User.query.filter_by(email=email).first()
    if user:
        # Generate a password reset token
        token = user.get_reset_token(expires_sec=app.config['PASSWORD_RESET_TOKEN_EXPIRATION'])
        
        # In a real application, you would now send this token via email to the user.
        app.logger.info(f"Password reset token for {user.email}: {token}")

        # IMPORTANT: For security, always return a generic success message
        # to prevent attackers from enumerating valid email addresses.
        return jsonify({"message": "If an account with that email exists, a password reset link has been sent."}), 200
    else:
        # If user not found, still return a generic success message for security
        return jsonify({"message": "If an account with that email exists, a password reset link has been sent."}), 200
    


@app.route('/reset-password', methods=['POST'])
def reset_password_with_token():
    """
    Handles the actual password reset using a provided token and new password.
    """
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('new_password')

    if not token or not new_password:
        return jsonify({"error": "Missing token or new_password"}), 400

    # Verify the reset token
    user = User.verify_reset_token(token)
    if not user:
        return jsonify({"error": "Invalid or expired token"}), 400

    try:
        # Update the user's password
        user.set_password(new_password)
        user.updated_at = datetime.datetime.now() # Update timestamp
        db.session.commit()
        return jsonify({"message": "Password has been reset successfully."}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error resetting password for user {user.id}: {e}")
        return jsonify({"error": "Failed to reset password."}), 500
    

@app.route('/users/<int:user_id>/verify', methods=['PUT'])
def verify_user_email(user_id):
    """
    Updates a user's email verification status.
    Expected payload: {"is_verified": true/false}
    """
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    if not data or 'is_verified' not in data:
        return jsonify({"error": "Missing 'is_verified' field in request body"}), 400

    is_verified_status = data['is_verified']
    if not isinstance(is_verified_status, bool):
        return jsonify({"error": "'is_verified' must be a boolean value (true/false)"}), 400

    try:
        user.is_verified = is_verified_status
        user.updated_at = datetime.datetime.now() # Update timestamp
        db.session.commit()
        
        # Return the updated user data, including the new verification status
        return jsonify(user.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating verification status for user {user_id}: {e}")
        return jsonify({"error": "Failed to update user verification status", "details": str(e)}), 500
    

@app.route('/static/profile_pics/<filename>')
def serve_profile_pic(filename):
    """Serves static profile picture files."""
    return send_from_directory(UPLOAD_FOLDER, filename)



if __name__ == '__main__':
    with app.app_context():
        # Ensure database tables are created when app is run directly
        db.create_all()
    app.run(port=5002, debug=True)
