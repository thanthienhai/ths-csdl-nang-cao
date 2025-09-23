"""
Database utility functions
"""
from app import db
from app.models.user import User
from app.models.product import Product, Category

def create_sample_data():
    """Create sample data for development and testing"""
    try:
        # Create sample categories
        categories_data = [
            {'name': 'Electronics', 'description': 'Electronic devices and gadgets'},
            {'name': 'Clothing', 'description': 'Apparel and fashion items'},
            {'name': 'Books', 'description': 'Books and educational materials'},
            {'name': 'Sports', 'description': 'Sports equipment and accessories'}
        ]
        
        categories = []
        for cat_data in categories_data:
            category = Category(**cat_data)
            category.save()
            categories.append(category)
        
        # Create sample users
        users_data = [
            {
                'username': 'admin',
                'email': 'admin@example.com',
                'full_name': 'System Administrator',
                'role': 'admin'
            },
            {
                'username': 'user1',
                'email': 'user1@example.com',
                'full_name': 'John Doe',
                'role': 'user'
            },
            {
                'username': 'user2',
                'email': 'user2@example.com',
                'full_name': 'Jane Smith',
                'role': 'user'
            }
        ]
        
        for user_data in users_data:
            user = User(**user_data)
            user.save()
        
        # Create sample products
        products_data = [
            {
                'name': 'Laptop Dell XPS 13',
                'description': 'High-performance ultrabook with 13-inch display',
                'price': 1299.99,
                'stock_quantity': 15,
                'sku': 'DELL-XPS13-001',
                'category_id': categories[0].id  # Electronics
            },
            {
                'name': 'Smartphone iPhone 14',
                'description': 'Latest iPhone with advanced camera system',
                'price': 999.99,
                'stock_quantity': 25,
                'sku': 'APPL-IP14-001',
                'category_id': categories[0].id  # Electronics
            },
            {
                'name': 'T-Shirt Cotton Basic',
                'description': 'Comfortable cotton t-shirt in various colors',
                'price': 19.99,
                'stock_quantity': 100,
                'sku': 'CLTH-TSH-001',
                'category_id': categories[1].id  # Clothing
            },
            {
                'name': 'Database Design Book',
                'description': 'Comprehensive guide to database design and optimization',
                'price': 49.99,
                'stock_quantity': 30,
                'sku': 'BOOK-DB-001',
                'category_id': categories[2].id  # Books
            },
            {
                'name': 'Tennis Racket Wilson Pro',
                'description': 'Professional tennis racket for advanced players',
                'price': 159.99,
                'stock_quantity': 12,
                'sku': 'SPRT-TNS-001',
                'category_id': categories[3].id  # Sports
            }
        ]
        
        for product_data in products_data:
            product = Product(**product_data)
            product.save()
        
        return True, "Sample data created successfully"
        
    except Exception as e:
        return False, f"Error creating sample data: {str(e)}"

def reset_database():
    """Reset the database by dropping and recreating all tables"""
    try:
        db.drop_all()
        db.create_all()
        return True, "Database reset successfully"
    except Exception as e:
        return False, f"Error resetting database: {str(e)}"