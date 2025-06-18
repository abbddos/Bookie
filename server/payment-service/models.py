from database import db # Corrected: Relative import for db
import datetime

class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(255), nullable=False) # ID from Order Service
    user_id = db.Column(db.String(255), nullable=False)  # ID from User Service
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), nullable=False) # e.g., 'USD', 'EUR'
    payment_method = db.Column(db.String(50), nullable=False) # e.g., 'credit_card', 'paypal'
    transaction_id = db.Column(db.String(255), unique=True, nullable=False) # Simulated gateway transaction ID
    status = db.Column(db.String(50), default='pending', nullable=False) # e.g., 'pending', 'completed', 'failed', 'refunded'
    payment_date = db.Column(db.DateTime, default=datetime.datetime.now, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    def __init__(self, order_id, user_id, amount, currency, payment_method, transaction_id, status='pending'):
        self.order_id = order_id
        self.user_id = user_id
        self.amount = amount
        self.currency = currency
        self.payment_method = payment_method
        self.transaction_id = transaction_id
        self.status = status

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'user_id': self.user_id,
            'amount': self.amount,
            'currency': self.currency,
            'payment_method': self.payment_method,
            'transaction_id': self.transaction_id,
            'status': self.status,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<Payment {self.id} for Order {self.order_id} - Status: {self.status}>'
