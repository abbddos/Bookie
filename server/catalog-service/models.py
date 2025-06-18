from database import db
import datetime

class Catalog(db.Model): # RENAMED: from Book to Catalog
    __tablename__ = 'catalog_item' # RENAMED: from book to catalog_item

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    isbn = db.Column(db.String(13), unique=True, nullable=False) # ISBN-13 is standard
    price = db.Column(db.Float, nullable=False)
    stock_quantity = db.Column(db.Integer, nullable=False, default=0) # MODIFIED: added default value
    description = db.Column(db.Text, nullable=True)
    publisher = db.Column(db.String(255), nullable=True) # NEW FIELD: Publisher
    cover_image_filename = db.Column(db.String(255), nullable=True) # RENAMED & REPURPOSED: from cover_image_url to cover_image_filename

    created_at = db.Column(db.DateTime, default=datetime.datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    def __init__(self, title, author, isbn, price, stock_quantity=0, description=None, publisher=None, cover_image_filename=None): # MODIFIED: added publisher, default stock_quantity, cover_image_filename
        self.title = title
        self.author = author
        self.isbn = isbn
        self.price = price
        self.stock_quantity = stock_quantity
        self.description = description
        self.publisher = publisher # NEW
        self.cover_image_filename = cover_image_filename # MODIFIED

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'isbn': self.isbn,
            'price': self.price,
            'stock_quantity': self.stock_quantity,
            'description': self.description,
            'publisher': self.publisher, # NEW
            'cover_image_filename': self.cover_image_filename, # MODIFIED
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<Catalog {self.title} by {self.author}>' # MODIFIED: Catalog instead of Book