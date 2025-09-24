from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # Database settings
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "legal_documents")
    
    # MongoDB Atlas settings
    MONGODB_USERNAME: Optional[str] = os.getenv("MONGODB_USERNAME")
    MONGODB_PASSWORD: Optional[str] = os.getenv("MONGODB_PASSWORD")
    MONGODB_CLUSTER: Optional[str] = os.getenv("MONGODB_CLUSTER")
    MONGODB_OPTIONS: str = os.getenv("MONGODB_OPTIONS", "retryWrites=true&w=majority")
    
    # Connection preferences
    USE_ATLAS: bool = os.getenv("USE_ATLAS", "true").lower() == "true"
    SSL_CERT_VALIDATION: bool = os.getenv("SSL_CERT_VALIDATION", "false").lower() == "true"
    
    # AI settings
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    SENTENCE_TRANSFORMER_MODEL: str = os.getenv("SENTENCE_TRANSFORMER_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    
    # Gemini settings
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # File upload settings
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))  # 10MB
    ALLOWED_EXTENSIONS: list = [".pdf", ".doc", ".docx", ".txt"]
    
    class Config:
        env_file = ".env"

# Create settings instance
settings = Settings()