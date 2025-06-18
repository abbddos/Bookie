from flask import Flask, request, jsonify
from flask_cors import CORS
from models import Payment
from database import db, init_db # Import db and init_db
from config import Config
import datetime
import uuid # For generating unique transaction IDs
import random # For simulating payment success/failure

app = Flask(__name__)
app.config.from_object(Config)
init_db(app) # Initialize db with the app first

CORS(app, resources={r"/*": {"origins": Config.CORS_ORIGINS}})

@app.route('/')
def home():
    return jsonify({"message": "Payment Service is running!", "status": "OK"})


@app.route('/payments', methods=['POST'])
def initiate_payment():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON data"}), 400

    order_id = data.get('order_id')
    user_id = data.get('user_id')
    amount = data.get('amount')
    currency = data.get('currency')
    payment_method = data.get('payment_method')

    if not all([order_id, user_id, amount, currency, payment_method]):
        return jsonify({"error": "Missing order_id, user_id, amount, currency, or payment_method"}), 400
    
    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({"error": "Amount must be positive"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount type"}), 400

    # Simulate a transaction ID from a payment gateway
    transaction_id = str(uuid.uuid4())

    # Simulate payment status (e.g., 80% success rate)
    simulated_status = 'completed' if random.random() < 0.8 else 'failed'

    try:
        new_payment = Payment(
            order_id=order_id,
            user_id=user_id,
            amount=amount,
            currency=currency,
            payment_method=payment_method,
            transaction_id=transaction_id,
            status=simulated_status # Set the simulated status
        )
        db.session.add(new_payment)
        db.session.commit()
        return jsonify(new_payment.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error initiating payment: {e}")
        return jsonify({"error": "Failed to initiate payment", "details": str(e)}), 500




@app.route('/payments', methods=['GET'])
def get_all_payments():
    payments = Payment.query.all()
    return jsonify([payment.to_dict() for payment in payments]), 200




@app.route('/payments/<int:payment_id>', methods=['GET'])
def get_payment(payment_id):
    payment = Payment.query.get(payment_id)
    if not payment:
        return jsonify({"error": "Payment not found"}), 404
    return jsonify(payment.to_dict()), 200




# Corrected route decorator for get_payments_by_order
@app.route('/payments/order/<string:order_id>', methods=['GET'])
def get_payments_by_order(order_id): # Corrected to take order_id from URL
    """
    Retrieves all payments associated with a given order_id.
    """
    payments = Payment.query.filter_by(order_id=order_id).all()
    if not payments:
        # It's better to return 404 if no payments are found for a specific order ID
        return jsonify({"error": f"No payments found for order_id: {order_id}"}), 404
    return jsonify([payment.to_dict() for payment in payments]), 200




@app.route('/payments/<int:payment_id>/status', methods=['PUT'])
def update_payment_status(payment_id):
    payment = Payment.query.get(payment_id)
    if not payment:
        return jsonify({"error": "Payment not found"}), 404
    
    data = request.get_json()
    new_status = data.get('status')
    if not new_status:
        return jsonify({"error": "Status field is required"}), 400
    
    allowed_statuses = ['pending', 'completed', 'failed', 'refunded', 'disputed']
    if new_status not in allowed_statuses:
        return jsonify({"error": f"Invalid status. Allowed statuses are: {', '.join(allowed_statuses)}"}), 400

    try:
        payment.status = new_status
        payment.updated_at = datetime.datetime.now()
        db.session.commit()
        return jsonify(payment.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating payment {payment_id}: {e}")
        return jsonify({"error": "Failed to update payment status", "details": str(e)}), 500




@app.route('/payments/<int:payment_id>', methods=['DELETE'])
def delete_payment(payment_id):
    payment = Payment.query.get(payment_id)
    if not payment:
        return jsonify({"error": "Payment not found"}), 404
    
    try:
        db.session.delete(payment)
        db.session.commit()
        return jsonify({"message": f"Payment {payment_id} deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting payment {payment_id}: {e}")
        return jsonify({"error": "Failed to delete payment", "details": str(e)}), 500




if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(port=5005, debug=True)
