from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import requests # For making HTTP requests to other microservices
from flask_jwt_extended import JWTManager # For JWT handling
from flask_mail import Mail # Import Mail
import json

from config import Config # Import our configuration

app = Flask(__name__)

# Apply CORS to the API Gateway
CORS(app, resources={r"/*": {"origins": Config.CORS_ORIGINS}})

# Configure Flask app with settings from Config object
app.config.from_object(Config)

app.json_encoder = json.JSONEncoder


# Initialize JWTManager with the app
jwt = JWTManager(app)

# Initialize Flask-Mail
mail = Mail(app)


# --- Blueprint Imports ---
from routes.users import users_bp # Import the users blueprint
from routes.catalog import catalog_bp # Import the catalog blueprint
from routes.payments import payments_bp # Import the payments blueprint
from routes.orders import orders_bp


# --- Blueprint Registrations ---
app.register_blueprint(users_bp, url_prefix='/users') # Register the users blueprint
app.register_blueprint(catalog_bp, url_prefix='/catalog') # Register the catalog blueprint
app.register_blueprint(payments_bp, url_prefix='/payments') # Register the payments blueprint
# app.register_blueprint(orders_bp, url_prefix='/orders')


@app.route('/')
def home():
    """Root endpoint for the API Gateway."""
    return jsonify({"message": "API Gateway is running!", "status": "OK", "version": "1.0"})

if __name__ == '__main__':
    # The API Gateway typically runs on a standard port like 5000
    app.run(port=Config.API_GATEWAY_PORT, debug=True)