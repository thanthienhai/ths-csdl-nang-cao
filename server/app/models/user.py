"""
User model for authentication and user management
"""
from app import db
from app.models.base import BaseModel

class User(BaseModel):
    """User model"""
    __tablename__ = 'users'
    
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    full_name = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    role = db.Column(db.String(50), default='user')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self):
        """Convert to dictionary, excluding sensitive data"""
        data = super().to_dict()
        data.pop('password_hash', None)  # Remove password hash from output
        return data