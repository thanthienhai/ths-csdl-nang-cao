"""
Product model for e-commerce or inventory management
"""
from app import db
from app.models.base import BaseModel

class Category(BaseModel):
    """Product category model"""
    __tablename__ = 'categories'
    
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship
    products = db.relationship('Product', backref='category', lazy=True)
    
    def __repr__(self):
        return f'<Category {self.name}>'

class Product(BaseModel):
    """Product model"""
    __tablename__ = 'products'
    
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock_quantity = db.Column(db.Integer, default=0)
    sku = db.Column(db.String(50), unique=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Foreign key
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    
    def __repr__(self):
        return f'<Product {self.name}>'
    
    def to_dict(self):
        """Convert to dictionary with category information"""
        data = super().to_dict()
        if self.category:
            data['category_name'] = self.category.name
        return data