"""
Main API Blueprint and routes
"""
from flask import Blueprint, jsonify, request
from app import db
from app.models.user import User
from app.models.product import Product, Category

# Create API blueprint
api_bp = Blueprint('api', __name__)

# Import and register sub-blueprints
from app.routes.users import user_bp
from app.routes.products import product_bp

api_bp.register_blueprint(user_bp, url_prefix='/users')
api_bp.register_blueprint(product_bp, url_prefix='/products')

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'API server is running'
    })

@api_bp.route('/info', methods=['GET'])
def api_info():
    """API information endpoint"""
    return jsonify({
        'name': 'THS Advanced Database API',
        'version': '1.0.0',
        'description': 'Backend API for advanced database course project',
        'endpoints': {
            'users': '/api/users',
            'products': '/api/products',
            'categories': '/api/categories'
        }
    })

# Error handlers
@api_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@api_bp.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400

@api_bp.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500