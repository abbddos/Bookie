from flask import Flask, request, jsonify, send_from_directory # Added send_from_directory
from flask_cors import CORS
from models import Catalog # MODIFIED: from Book to Catalog
from database import db, init_db
from config import Config
import os
from werkzeug.utils import secure_filename # NEW: For file uploads
import uuid # NEW: For unique filenames
from PIL import Image # NEW: For image processing

app = Flask(__name__)
app.config.from_object(Config)
init_db(app)

# NEW: Constants for file uploads and image processing (from Config)
UPLOAD_FOLDER = Config.UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True) # Ensure upload directory exists

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
TARGET_COVER_IMAGE_SIZE = (400, 600) # Example size for book covers (width, height) - adjust as needed

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_cover_image(filepath):
    """
    Resizes an image saved at filepath to TARGET_COVER_IMAGE_SIZE.
    Saves the resized image, overwriting the original.
    Returns the original filepath (as the file is processed in place).
    """
    try:
        img = Image.open(filepath)

        # Resize image: maintain aspect ratio
        img.thumbnail(TARGET_COVER_IMAGE_SIZE, Image.Resampling.LANCZOS) 

        # Save the processed image back to the original path, preserving original format
        # If original was PNG, it will be saved back as PNG, etc.
        img.save(filepath) 
        return filepath

    except Exception as e:
        app.logger.error(f"Error processing cover image {filepath}: {e}")
        return filepath # Return original path, indicating processing failed.


CORS(app, resources={r"/*": {"origins": Config.CORS_ORIGINS}})

@app.route('/')
def home():
    return jsonify({"message": "Catalog Service is running!", "status": "OK"})


#-- Basic CRUD API --#
# NEW ROUTES: Renamed from /books to /catalog for consistency with model name
@app.route('/catalog', methods=['POST'])
def create_catalog_item(): # MODIFIED: from create_book to create_catalog_item
    # Check if request is JSON or form-data
    if request.content_type and 'application/json' in request.content_type:
        data = request.get_json()
    else: # Assume form-data, typically for file uploads
        data = request.form
    
    if not data:
        return jsonify({"error": "Invalid data, expected JSON or form-data"}), 400

    required_fields = ['title', 'author', 'isbn', 'price'] # stock_quantity now has a default
    if not all(field in data for field in required_fields):
        return jsonify({"error": f"Missing one or more required fields: {', '.join(required_fields)}"}), 400

    # Basic type validation
    try:
        price = float(data['price'])
        # Use .get with default for stock_quantity
        stock_quantity = int(data.get('stock_quantity', 0)) 
        if price <= 0 or stock_quantity < 0: # stock_quantity can now be 0
            return jsonify({"error": "Price must be positive, stock_quantity must be non-negative"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid type for price or stock_quantity"}), 400

    # Check for existing ISBN
    if Catalog.query.filter_by(isbn=data['isbn']).first(): # MODIFIED: Catalog.query
        return jsonify({"error": "Catalog item with this ISBN already exists"}), 409

    cover_image_filename = None
    if 'cover_image' in request.files and request.files['cover_image'].filename != '':
        file = request.files['cover_image']
        if file and allowed_file(file.filename):
            filename_orig = secure_filename(file.filename)
            unique_filename = str(uuid.uuid4()) + '_' + filename_orig
            file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            try:
                file.save(file_path)
                processed_file_path = process_cover_image(file_path) # Process the saved image
                cover_image_filename = os.path.basename(processed_file_path) # Store just the filename
            except Exception as e:
                app.logger.error(f"Error during cover image save/process for create_catalog_item: {e}")
                return jsonify({"error": "Failed to save or process cover image"}), 500
        else:
            return jsonify({"error": "Invalid file type for cover image"}), 400
    elif 'cover_image_filename' in data: # Allows setting by filename directly if no file uploaded
        cover_image_filename = data.get('cover_image_filename')

    try:
        new_catalog_item = Catalog( # MODIFIED: Catalog
            title=data['title'],
            author=data['author'],
            isbn=data['isbn'],
            price=price,
            stock_quantity=stock_quantity,
            description=data.get('description'),
            publisher=data.get('publisher'), # NEW
            cover_image_filename=cover_image_filename # MODIFIED
        )
        db.session.add(new_catalog_item)
        db.session.commit()
        return jsonify(new_catalog_item.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creating catalog item: {e}")
        return jsonify({"error": "Failed to create catalog item", "details": str(e)}), 500
    

@app.route('/catalog', methods=['GET'])
def get_all_catalog_items(): # MODIFIED: from get_all_books to get_all_catalog_items
    catalog_items = Catalog.query.all() # MODIFIED: Catalog.query
    # Construct full image URLs for response
    items_with_urls = []
    for item in catalog_items:
        item_dict = item.to_dict()
        if item_dict['cover_image_filename']:
            item_dict['cover_image_url'] = f"/static/cover_images/{item_dict['cover_image_filename']}"
        else:
            item_dict['cover_image_url'] = None # Ensure a clear URL if no image
        items_with_urls.append(item_dict)
    return jsonify(items_with_urls), 200


@app.route('/catalog/<int:item_id>', methods=['GET'])
def get_catalog_item(item_id): # MODIFIED: from get_book to get_catalog_item
    catalog_item = Catalog.query.get(item_id) # MODIFIED: Catalog.query
    if not catalog_item:
        return jsonify({"error": "Catalog item not found"}), 404
    
    item_dict = catalog_item.to_dict()
    if item_dict['cover_image_filename']:
        item_dict['cover_image_url'] = f"/static/cover_images/{item_dict['cover_image_filename']}"
    else:
        item_dict['cover_image_url'] = None
    return jsonify(item_dict), 200


@app.route('/catalog/<int:item_id>', methods=['PUT'])
def update_catalog_item(item_id): # MODIFIED: from update_book to update_catalog_item
    catalog_item = Catalog.query.get(item_id) # MODIFIED: Catalog.query
    if not catalog_item:
        return jsonify({"error": "Catalog item not found"}), 404

    # Check if request is JSON or form-data
    if request.content_type and 'application/json' in request.content_type:
        data = request.get_json()
    else: # Assume form-data, typically for file uploads
        data = request.form

    if not data and not request.files:
        return jsonify({"error": "No data or files provided for update"}), 400

    try:
        if 'title' in data:
            catalog_item.title = data['title']
        if 'author' in data:
            catalog_item.author = data['author']
        if 'isbn' in data:
            # Check if ISBN is being changed to an existing one (excluding self)
            if Catalog.query.filter(Catalog.isbn == data['isbn'], Catalog.id != item_id).first(): # MODIFIED: Catalog.query
                return jsonify({"error": "Catalog item with this ISBN already exists"}), 409
            catalog_item.isbn = data['isbn']
        if 'price' in data:
            price = float(data['price'])
            if price <= 0:
                 return jsonify({"error": "Price must be positive"}), 400
            catalog_item.price = price
        if 'stock_quantity' in data:
            stock_quantity = int(data['stock_quantity'])
            if stock_quantity < 0:
                 return jsonify({"error": "Stock quantity must be non-negative"}), 400
            catalog_item.stock_quantity = stock_quantity
        if 'description' in data:
            catalog_item.description = data['description']
        if 'publisher' in data: # NEW
            catalog_item.publisher = data['publisher']
        
        # Handle cover image upload
        if 'cover_image' in request.files and request.files['cover_image'].filename != '':
            file = request.files['cover_image']
            if file and allowed_file(file.filename):
                filename_orig = secure_filename(file.filename)
                unique_filename = str(uuid.uuid4()) + '_' + filename_orig
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                try:
                    # Delete old cover image if it exists
                    if catalog_item.cover_image_filename and \
                       os.path.exists(os.path.join(UPLOAD_FOLDER, catalog_item.cover_image_filename)):
                        os.remove(os.path.join(UPLOAD_FOLDER, catalog_item.cover_image_filename))

                    file.save(file_path)
                    processed_file_path = process_cover_image(file_path) # Process the saved image
                    catalog_item.cover_image_filename = os.path.basename(processed_file_path) # Store just the filename
                except Exception as e:
                    app.logger.error(f"Error during cover image save/process for update_catalog_item: {e}")
                    return jsonify({"error": "Failed to save or process cover image"}), 500
            else:
                return jsonify({"error": "Invalid file type for cover image"}), 400
        elif 'cover_image_filename' in data: # Allows setting by filename directly or clearing it
            catalog_item.cover_image_filename = data.get('cover_image_filename')
        
        db.session.commit()
        
        # Construct full image URL for response
        item_dict = catalog_item.to_dict()
        if item_dict['cover_image_filename']:
            item_dict['cover_image_url'] = f"/static/cover_images/{item_dict['cover_image_filename']}"
        else:
            item_dict['cover_image_url'] = None
        return jsonify(item_dict), 200
    except (ValueError, TypeError):
        db.session.rollback()
        return jsonify({"error": "Invalid type for price or stock_quantity"}), 400
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating catalog item {item_id}: {e}")
        return jsonify({"error": "Failed to update catalog item", "details": str(e)}), 500



@app.route('/catalog/<int:item_id>', methods=['DELETE'])
def delete_catalog_item(item_id): # MODIFIED: from delete_book to delete_catalog_item
    catalog_item = Catalog.query.get(item_id) # MODIFIED: Catalog.query
    if not catalog_item:
        return jsonify({"error": "Catalog item not found"}), 404

    try:
        # Delete associated cover image file if it exists
        if catalog_item.cover_image_filename and \
           os.path.exists(os.path.join(UPLOAD_FOLDER, catalog_item.cover_image_filename)):
            os.remove(os.path.join(UPLOAD_FOLDER, catalog_item.cover_image_filename))

        db.session.delete(catalog_item) # MODIFIED: catalog_item
        db.session.commit()
        return jsonify({"message": f"Catalog item {item_id} deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting catalog item {item_id}: {e}")
        return jsonify({"error": "Failed to delete catalog item", "details": str(e)}), 500




# NEW ROUTE: To serve static cover images
@app.route('/static/cover_images/<filename>')
def serve_cover_image(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(port=5003, debug=True)

