"""
Product management endpoints
"""
from flask import Blueprint, jsonify, request
from app import db
from app.models.product import Product, Category

product_bp = Blueprint('products', __name__)

@product_bp.route('/', methods=['GET'])
def get_products():
    """Get all products"""
    try:
        products = Product.query.all()
        return jsonify({
            'success': True,
            'data': [product.to_dict() for product in products],
            'count': len(products)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@product_bp.route('/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """Get product by ID"""
    try:
        product = Product.query.get_or_404(product_id)
        return jsonify({
            'success': True,
            'data': product.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 404

@product_bp.route('/', methods=['POST'])
def create_product():
    """Create new product"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'price']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False, 
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Create new product
        product = Product(
            name=data['name'],
            description=data.get('description'),
            price=data['price'],
            stock_quantity=data.get('stock_quantity', 0),
            sku=data.get('sku'),
            category_id=data.get('category_id')
        )
        
        product.save()
        
        return jsonify({
            'success': True,
            'message': 'Product created successfully',
            'data': product.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@product_bp.route('/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """Update product"""
    try:
        product = Product.query.get_or_404(product_id)
        data = request.get_json()
        
        # Update fields if provided
        updateable_fields = ['name', 'description', 'price', 'stock_quantity', 'sku', 'category_id', 'is_active']
        for field in updateable_fields:
            if field in data:
                setattr(product, field, data[field])
        
        product.save()
        
        return jsonify({
            'success': True,
            'message': 'Product updated successfully',
            'data': product.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@product_bp.route('/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Delete product"""
    try:
        product = Product.query.get_or_404(product_id)
        product.delete()
        
        return jsonify({
            'success': True,
            'message': 'Product deleted successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Category endpoints
@product_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get all categories"""
    try:
        categories = Category.query.all()
        return jsonify({
            'success': True,
            'data': [category.to_dict() for category in categories],
            'count': len(categories)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@product_bp.route('/categories', methods=['POST'])
def create_category():
    """Create new category"""
    try:
        data = request.get_json()
        
        if 'name' not in data:
            return jsonify({
                'success': False, 
                'error': 'Missing required field: name'
            }), 400
        
        category = Category(
            name=data['name'],
            description=data.get('description')
        )
        
        category.save()
        
        return jsonify({
            'success': True,
            'message': 'Category created successfully',
            'data': category.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500