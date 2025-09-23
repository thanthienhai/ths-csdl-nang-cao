"""
Base model class with common functionality
"""
from datetime import datetime
from app import db

class BaseModel(db.Model):
    """Base model with common fields"""
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def save(self):
        """Save the current instance"""
        db.session.add(self)
        db.session.commit()
        
    def delete(self):
        """Delete the current instance"""
        db.session.delete(self)
        db.session.commit()
        
    def to_dict(self):
        """Convert model to dictionary"""
        return {column.name: getattr(self, column.name) 
                for column in self.__table__.columns}