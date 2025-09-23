"""
Main application entry point
"""
import os
import sys
# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.utils.database import create_sample_data, reset_database

# Create Flask application
app = create_app(os.getenv('FLASK_ENV', 'development'))

@app.cli.command('init-db')
def init_db():
    """Initialize database with tables"""
    from app import db
    db.create_all()
    print("Database tables created successfully!")

@app.cli.command('seed-db')
def seed_db():
    """Seed database with sample data"""
    success, message = create_sample_data()
    print(message)

@app.cli.command('reset-db')
def reset_db():
    """Reset database and recreate tables"""
    success, message = reset_database()
    print(message)

if __name__ == '__main__':
    # For development server
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=True
    )