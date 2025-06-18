from flask import Flask, request, jsonify
from flask_cors import CORS
from models import Order, OrderItem 
from database import db, init_db
from config import Config
import datetime


app = Flask(__name__)
app.config.from_object(Config)
init_db(app)

CORS(app, resources={r"/*": {"origins": Config.CORS_ORIGINS}})


@app.route('/')
def home():
    return jsonify({"message": "Order Service is running!", "status": "OK"})


#-- Basic CRUD API --#
@app.route('/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON data"}), 400

    user_id = data.get('user_id')
    shipping_address = data.get('shipping_address')
    items_data = data.get('items')

    if not user_id or not shipping_address or not items_data:
        return jsonify({"error": "Missing user_id, shipping_address, or items"}), 400
    
    if not isinstance(items_data, list) or not items_data:
        return jsonify({"error": "Items must be a non-empty list"}), 400

    new_order = Order(user_id=user_id, shipping_address=shipping_address)
    
    # Use a transaction to ensure atomicity for order creation and its items
    try:
        db.session.add(new_order)
        db.session.flush() # Flush to get the order.id before committing

        total_amount = 0.0
        for item_data in items_data:
            book_id = item_data.get('book_id')
            quantity = item_data.get('quantity')
            price_at_purchase = item_data.get('price_at_purchase')

            if not book_id or not quantity or price_at_purchase is None:
                db.session.rollback()
                return jsonify({"error": "Each item must have book_id, quantity, and price_at_purchase"}), 400
            
            try:
                quantity = int(quantity)
                price_at_purchase = float(price_at_purchase)
                if quantity <= 0 or price_at_purchase <= 0:
                    db.session.rollback()
                    return jsonify({"error": "Quantity and price_at_purchase must be positive for items"}), 400
            except (ValueError, TypeError):
                db.session.rollback()
                return jsonify({"error": "Invalid type for quantity or price_at_purchase in items"}), 400

            new_order_item = OrderItem(
                order_id=new_order.id, # Link to the newly created order
                book_id=book_id,
                quantity=quantity,
                price_at_purchase=price_at_purchase
            )
            db.session.add(new_order_item)
            total_amount += (quantity * price_at_purchase)
        
        new_order.total_amount = total_amount # Set calculated total amount
        db.session.commit()
        return jsonify(new_order.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creating order: {e}")
        return jsonify({"error": "Failed to create order", "details": str(e)}), 500
    


@app.route('/orders', methods=['GET'])
def get_all_orders():
    # In a real app, you might want pagination and user-specific orders
    orders = Order.query.all()
    return jsonify([order.to_dict() for order in orders]), 200 


@app.route('/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    return jsonify(order.to_dict()), 200


@app.route('/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    
    data = request.get_json()
    new_status = data.get('status')
    if not new_status:
        return jsonify({"error": "Status field is required"}), 400
    
    # Optional: Validate status against a predefined list
    allowed_statuses = ['pending', 'processing', 'shipped', 'cancelled', 'delivered']
    if new_status not in allowed_statuses:
        return jsonify({"error": f"Invalid status. Allowed statuses are: {', '.join(allowed_statuses)}"}), 400

    try:
        order.status = new_status
        order.updated_at = datetime.datetime.now() # Manually update timestamp for status change
        db.session.commit()
        return jsonify(order.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating order {order_id} status: {e}")
        return jsonify({"error": "Failed to update order status", "details": str(e)}), 500
    


@app.route('/orders/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    
    try:
        # Due to cascade="all, delete-orphan" in Order model relationship,
        # deleting the Order will automatically delete its associated OrderItems.
        db.session.delete(order)
        db.session.commit()
        return jsonify({"message": f"Order {order_id} and its items deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting order {order_id}: {e}")
        return jsonify({"error": "Failed to delete order", "details": str(e)}), 500
    


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(port=5004, debug=True)