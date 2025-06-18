from database import db
import datetime

class Order(db.Model):
    __tablename__ = 'orders' # Using 'orders' plural for table name

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), nullable=False) # Storing user_id from user-service
    order_date = db.Column(db.DateTime, default=datetime.datetime.now, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='pending', nullable=False) # e.g., 'pending', 'processing', 'shipped', 'cancelled'
    shipping_address = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    # Relationship to OrderItem: 'cascade="all, delete-orphan"' means if an Order is deleted,
    # all its associated OrderItems are also deleted.
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")

    def __init__(self, user_id, shipping_address):
        self.user_id = user_id
        self.shipping_address = shipping_address
        self.total_amount = 0.0 # Will be calculated based on items

    def calculate_total_amount(self):
        self.total_amount = sum(item.quantity * item.price_at_purchase for item in self.items)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'total_amount': self.total_amount,
            'status': self.status,
            'shipping_address': self.shipping_address,
            'items': [item.to_dict() for item in self.items], # Include nested items
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<Order {self.id} by User {self.user_id} - Status: {self.status}>'

class OrderItem(db.Model):
    __tablename__ = 'order_items' # Using 'order_items' plural

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False) # Foreign Key to Order
    book_id = db.Column(db.String(255), nullable=False) # Storing book_id from catalog-service
    quantity = db.Column(db.Integer, nullable=False)
    price_at_purchase = db.Column(db.Float, nullable=False) # Price at the time of order

    created_at = db.Column(db.DateTime, default=datetime.datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    def __init__(self, order_id, book_id, quantity, price_at_purchase):
        self.order_id = order_id
        self.book_id = book_id
        self.quantity = quantity
        self.price_at_purchase = price_at_purchase

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'book_id': self.book_id,
            'quantity': self.quantity,
            'price_at_purchase': self.price_at_purchase,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<OrderItem {self.id} for Order {self.order_id} - Book {self.book_id}>'