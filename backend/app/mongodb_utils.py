"""
MongoDB Atlas Connection Utility
Utility functions for connecting to MongoDB Atlas
"""

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import asyncio
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)

def get_mongodb_uri() -> str:
    """
    Construct MongoDB connection URI
    
    Priority:
    1. If USE_ATLAS is True and Atlas credentials are provided, use MongoDB Atlas
    2. Otherwise, use MONGODB_URL or default local connection
    """
    if (settings.USE_ATLAS and 
        settings.MONGODB_USERNAME and 
        settings.MONGODB_PASSWORD and 
        settings.MONGODB_CLUSTER):
        
        # URL encode the password to handle special characters
        import urllib.parse
        encoded_password = urllib.parse.quote_plus(settings.MONGODB_PASSWORD)
        
        # Build base URI
        atlas_uri = (f"mongodb+srv://{settings.MONGODB_USERNAME}:"
                     f"{encoded_password}@{settings.MONGODB_CLUSTER}/"
                     f"{settings.DATABASE_NAME}?{settings.MONGODB_OPTIONS}&appName=ths-cluster")
        
        # Add comprehensive SSL/TLS options for better compatibility
        ssl_options = [
            "tls=true",
            "tlsAllowInvalidCertificates=true",  # Allow invalid certificates (development)
            "tlsAllowInvalidHostnames=true",    # Allow invalid hostnames (development)
            "tlsInsecure=true"                   # Skip certificate verification completely
        ]
        atlas_uri += "&" + "&".join(ssl_options)
        
        logger.info("Using MongoDB Atlas connection")
        return atlas_uri
    else:
        logger.info(f"Using MongoDB connection: {settings.MONGODB_URL}")
        return settings.MONGODB_URL

def create_sync_client() -> MongoClient:
    """Create synchronous MongoDB client"""
    uri = get_mongodb_uri()
    
    if "mongodb+srv://" in uri:
        # MongoDB Atlas connection with comprehensive SSL/TLS options
        client_options = {
            "server_api": ServerApi('1'),
            "connectTimeoutMS": 60000,  # 60 seconds - increased timeout
            "socketTimeoutMS": 60000,   # 60 seconds - increased timeout
            "serverSelectionTimeoutMS": 60000,  # 60 seconds - increased timeout
            "maxPoolSize": 10,
            "retryWrites": True,
            # Comprehensive SSL/TLS options
            "tls": True,
            "tlsAllowInvalidCertificates": True,
            "tlsAllowInvalidHostnames": True,
            "tlsInsecure": True,
        }
        
        # Additional SSL context configuration for better compatibility
        import ssl
        try:
            # Create custom SSL context with relaxed security for development
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            client_options["ssl_context"] = ssl_context
        except Exception as e:
            logger.warning(f"Could not create custom SSL context: {e}")
        
        client = MongoClient(uri, **client_options)
    else:
        # Local or standard MongoDB connection
        client = MongoClient(uri)
    
    return client

def create_async_client() -> AsyncIOMotorClient:
    """Create asynchronous MongoDB client"""
    uri = get_mongodb_uri()
    
    if "mongodb+srv://" in uri:
        # MongoDB Atlas connection with comprehensive SSL/TLS options
        client_options = {
            "server_api": ServerApi('1'),
            "connectTimeoutMS": 60000,  # 60 seconds - increased timeout
            "socketTimeoutMS": 60000,   # 60 seconds - increased timeout
            "serverSelectionTimeoutMS": 60000,  # 60 seconds - increased timeout
            "maxPoolSize": 10,
            "retryWrites": True,
            # Comprehensive SSL/TLS options
            "tls": True,
            "tlsAllowInvalidCertificates": True,
            "tlsAllowInvalidHostnames": True,
            "tlsInsecure": True,
        }
        
        # Additional SSL context configuration for better compatibility
        import ssl
        try:
            # Create custom SSL context with relaxed security for development
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            client_options["ssl_context"] = ssl_context
        except Exception as e:
            logger.warning(f"Could not create custom SSL context: {e}")
            
        client = AsyncIOMotorClient(uri, **client_options)
    else:
        # Local or standard MongoDB connection
        client = AsyncIOMotorClient(uri)
    
    return client

async def test_connection() -> bool:
    """Test MongoDB connection"""
    try:
        client = create_async_client()
        await client.admin.command('ping')
        logger.info("Pinged your deployment. You successfully connected to MongoDB!")
        client.close()
        return True
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return False

def test_connection_sync() -> bool:
    """Test MongoDB connection (synchronous)"""
    try:
        client = create_sync_client()
        client.admin.command('ping')
        logger.info("Pinged your deployment. You successfully connected to MongoDB!")
        client.close()
        return True
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return False

if __name__ == "__main__":
    # Test connection when run directly
    print("Testing MongoDB connection...")
    
    # Test sync connection
    if test_connection_sync():
        print("✅ Synchronous connection successful!")
    else:
        print("❌ Synchronous connection failed!")
    
    # Test async connection
    async def test_async():
        if await test_connection():
            print("✅ Asynchronous connection successful!")
        else:
            print("❌ Asynchronous connection failed!")
    
    asyncio.run(test_async())