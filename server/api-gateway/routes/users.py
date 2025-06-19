from flask import Blueprint, request, Response, jsonify, url_for, current_app, redirect
import requests
from config import Config # Import our configuration
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from flask_mail import Message # Import Message for email
from itsdangerous import URLSafeTimedSerializer as Serializer, SignatureExpired, BadTimeSignature # For verification tokens
import datetime


# Create a Blueprint for user-related routes
users_bp = Blueprint('users_bp', __name__)

# Get the base URL for the User Service from config
USER_SERVICE_URL = Config.USER_SERVICE_URL

# --- Helper function for proxying requests ---
def _proxy_request(service_url, path, method=None, json_data=None, form_data=None, files=None):
    """
    Generic helper to proxy requests to a backend service.
    """
    full_url = f"{service_url}/{path}"
    
    req_method = method if method else request.method

    data_to_send = None
    headers_to_send = {key: value for key, value in request.headers if key.lower() not in ['host', 'content-length']}

    if json_data is not None:
        data_to_send = json_data
        headers_to_send['Content-Type'] = 'application/json'
    elif form_data is not None:
        data_to_send = form_data
    elif request.is_json:
        data_to_send = request.get_json()
        headers_to_send['Content-Type'] = 'application/json'
    else:
        data_to_send = request.get_data()
        if 'Content-Type' in request.headers:
            headers_to_send['Content-Type'] = request.headers['Content-Type']

    try:
        resp = requests.request(
            method=req_method,
            url=full_url,
            headers=headers_to_send,
            json=data_to_send if headers_to_send.get('Content-Type') == 'application/json' else None,
            data=data_to_send if headers_to_send.get('Content-Type') != 'application/json' else None,
            cookies=request.cookies,
            allow_redirects=False,
            params=request.args,
            files=files if files else (request.files if request.files else None)
        )

        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for name, value in resp.raw.headers.items() if name.lower() not in excluded_headers]

        return Response(resp.content, resp.status_code, headers)

    except requests.exceptions.ConnectionError:
        return jsonify({"error": f"{service_url.split('//')[1].split(':')[0].capitalize()} service is currently unavailable. Please try again later."}), 503
    except requests.exceptions.Timeout:
        return jsonify({"error": f"{service_url.split('//')[1].split(':')[0].capitalize()} service did not respond in time."}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"An error occurred while communicating with the {service_url.split('//')[1].split(':')[0].capitalize()} service: {str(e)}"}), 500


# --- Helper function to generate email verification token ---
def generate_email_verification_token(user_id, expires_sec=Config.EMAIL_VERIFICATION_TOKEN_EXPIRATION):
    s = Serializer(current_app.config['SECRET_KEY'], expires_sec)
    return s.dumps({'user_id': user_id}).decode('utf-8')

# --- Helper function to send verification email ---
def send_verification_email(user_email, user_id):
    # Import mail object here to avoid circular dependency if mail is initialized in app.py
    from app import mail # Assuming 'mail' object is initialized in app.py

    token = generate_email_verification_token(user_id)
    # The external_url_for generates a full URL for the verification endpoint
    # Ensure your API Gateway is accessible externally for this link to work
    verify_url = url_for('users_bp.verify_email', token=token, _external=True) # users_bp.verify_email refers to the blueprint and function name
    
    msg = Message('Verify Your Email Address',
                  sender=Config.MAIL_DEFAULT_SENDER,
                  recipients=[user_email])
    msg.body = f"""To verify your email address for the Bookstore App, please click on the following link:
{verify_url}

If you did not register for this account, please ignore this email.
"""
    
    try:
        mail.send(msg)
        current_app.logger.info(f"Verification email sent to {user_email}")
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send verification email to {user_email}: {e}")
        return False


# --- Existing Proxy Route for User Service (CRUD operations) ---
@users_bp.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE'])
@users_bp.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy_user_service(path):
    """
    Proxies general user-related CRUD requests to the User Service.
    """
    return _proxy_request(USER_SERVICE_URL, path)


# --- User Registration Endpoint (MODIFIED to send email) ---
@users_bp.route('/register', methods=['POST'])
def register_user():
    """
    Handles user registration.
    Forwards user creation request to user-service.
    If successful, generates a JWT and returns it.
    Also sends a verification email.
    """
    user_service_response = _proxy_request(USER_SERVICE_URL, 'users')

    if user_service_response.status_code == 201:
        user_data = user_service_response.get_json()

        access_token = create_access_token(identity=user_data['id'])
        
        # NEW: Send verification email
        email_sent = send_verification_email(user_data['email'], user_data['id'])
        
        response_data = {
            "message": "User registered successfully. Please check your email for verification.",
            "user": user_data,
            "access_token": access_token,
            "email_verification_sent": email_sent
        }
        return jsonify(response_data), 201
    else:
        return user_service_response


# --- User Login Endpoint (MODIFIED to check verification status) ---
@users_bp.route('/login', methods=['POST'])
def login_user():
    """
    Handles user login.
    Verifies credentials with user-service.
    If successful, generates and returns a JWT.
    Checks if the user's email is verified.
    """
    data = request.get_json()
    username_or_email = data.get('username_or_email')
    password = data.get('password')

    if not username_or_email or not password:
        return jsonify({"error": "Missing username/email or password"}), 400

    # Corrected login_payload key to match user-service expectation
    login_payload = {"username_or_email": username_or_email, "password": password}
    
    try:
        user_service_response = _proxy_request(USER_SERVICE_URL, 'login', method='POST', json_data=login_payload)
        
        if user_service_response.status_code == 200:
            user_data = user_service_response.get_json()
            
            # NEW: Check if user is verified before issuing token
            # This 'is_verified' field must be returned by your user-service's login endpoint
            if not user_data.get('is_verified'):
                return jsonify({"error": "Account not verified. Please check your email."}), 403

            access_token = create_access_token(identity=user_data['id'])

            response_data = {
                "message": "Login successful",
                "user": user_data,
                "access_token": access_token
            }
            return jsonify(response_data), 200
        else:
            return user_service_response

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred during login: {str(e)}"}), 500


# --- Forgot Password (Initiate Reset) Endpoint ---
@users_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """
    Handles initiating the password reset process.
    Forwards request to user-service to generate a reset token and send email.
    """
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({"error": "Email is required"}), 400

    reset_request_payload = {"email": email}
    user_service_response = _proxy_request(
        USER_SERVICE_URL, 'request-password-reset', method='POST', json_data=reset_request_payload
    )

    # Always return a generic success message for security, regardless of user existence
    return jsonify({"message": "If the email is registered, a password reset link has been sent."}), 200


# --- Reset Password (Confirm Reset) Endpoint ---
@users_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """
    Handles confirming the password reset with a token and new password.
    Forwards request to user-service to verify token and update password.
    """
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('new_password')

    if not token or not new_password:
        return jsonify({"error": "Missing token or new_password"}), 400

    reset_payload = {"token": token, "new_password": new_password}
    user_service_response = _proxy_request(
        USER_SERVICE_URL, 'reset-password', method='POST', json_data=reset_payload
    )

    return user_service_response


# --- Change Password (Authenticated User) Endpoint ---
@users_bp.route('/change-password', methods=['PUT'])
@jwt_required() # This decorator protects the route, requiring a valid JWT
def change_password():
    """
    Allows an authenticated user to change their password.
    Requires a valid JWT.
    Forwards request to user-service's specific password change endpoint.
    """
    current_user_id = get_jwt_identity() # Get the user ID from the JWT
    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')

    if not current_password or not new_password:
        return jsonify({"error": "Missing current_password or new_password"}), 400

    password_change_payload = {
        "current_password": current_password,
        "new_password": new_password
    }
    user_service_response = _proxy_request(
        USER_SERVICE_URL, f'users/{current_user_id}/password', method='PUT', json_data=password_change_payload
    )

    return user_service_response


# --- NEW: Email Verification Endpoint (MODIFIED to redirect) ---
@users_bp.route('/verify-email/<token>', methods=['GET'])
def verify_email(token):
    """
    Handles the email verification link.
    Verifies the token and instructs the user-service to mark the user as verified.
    Redirects to frontend success/failure pages.
    """
    s = Serializer(current_app.config['SECRET_KEY'])
    try:
        user_id = s.loads(token)['user_id']
    except SignatureExpired:
        current_app.logger.warning(f"Expired email verification token received: {token}")
        return redirect(Config.FRONTEND_VERIFICATION_FAILURE_URL + "?error=expired_token", code=302)
    except BadTimeSignature:
        current_app.logger.warning(f"Invalid email verification token received: {token}")
        return redirect(Config.FRONTEND_VERIFICATION_FAILURE_URL + "?error=invalid_token", code=302)
    except Exception as e:
        current_app.logger.error(f"Error loading verification token: {e}")
        return redirect(Config.FRONTEND_VERIFICATION_FAILURE_URL + "?error=internal_error", code=302)

    # Now, communicate with the user-service to mark the user as verified
    # We'll need a new endpoint in user-service like /users/<user_id>/verify
    verify_payload = {"is_verified": True}
    user_service_response = _proxy_request(
        USER_SERVICE_URL, f'users/{user_id}/verify', method='PUT', json_data=verify_payload
    )

    if user_service_response.status_code == 200:
        current_app.logger.info(f"User {user_id} email successfully verified.")
        return redirect(Config.FRONTEND_VERIFICATION_SUCCESS_URL, code=302)
    else:
        current_app.logger.error(f"User service failed to verify user {user_id}: {user_service_response.status_code} - {user_service_response.text}")
        # Pass through the error from user-service if verification failed there
        # Or redirect to a more specific error page
        return redirect(Config.FRONTEND_VERIFICATION_FAILURE_URL + "?error=service_error", code=302)
