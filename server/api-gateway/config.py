import os

class Config:
    # Define the port for the API Gateway itself
    API_GATEWAY_PORT = 5000

    # Define the base URLs for your backend microservices
    USER_SERVICE_URL = "http://127.0.0.1:5002"
    CATALOG_SERVICE_URL = "http://127.0.0.1:5003"
    ORDER_SERVICE_URL = "http://127.0.0.1:5004"
    PAYMENT_SERVICE_URL = "http://127.0.0.1:5005"

    # CORS Configuration
    CORS_ORIGINS = ["http://localhost:3000"]

    # Secret key for Flask sessions and JWT signing
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_very_secret_key_for_the_api_gateway'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'super-secret-jwt-key-change-this-in-production'

    # Email Configuration for Flask-Mail
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.googlemail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'your_email@example.com' # Replace with your email
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or 'your_email_password' # Replace with your app password/password
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@yourdomain.com'
    
    # Expiry time for email verification tokens (e.g., 24 hours = 86400 seconds)
    EMAIL_VERIFICATION_TOKEN_EXPIRATION = 86400

    # Frontend URLs for email verification redirects
    FRONTEND_VERIFICATION_SUCCESS_URL = "http://localhost:3000/verify-success"
    FRONTEND_VERIFICATION_FAILURE_URL = "http://localhost:3000/verify-failure"