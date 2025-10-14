from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
import logging

from app.config import settings
from app.database import get_database, create_indexes
from app.mongodb_utils import create_async_client
from app.routers import documents, search, qa
from app.routers import crawling, enhanced_processing, advanced_search, text_analysis, reports

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def connect_with_fallback():
    """Connect to MongoDB with fallback strategies"""
    import asyncio
    from pymongo.errors import ServerSelectionTimeoutError, AutoReconnect
    
    connection_attempts = [
        ("MongoDB Atlas (Primary)", lambda: create_async_client()),
        ("MongoDB Atlas (Fallback)", lambda: create_fallback_client()),
        ("Local MongoDB", lambda: create_local_client()),
    ]
    
    for attempt_name, client_factory in connection_attempts:
        logger.info(f"Attempting connection: {attempt_name}")
        try:
            client = client_factory()
            # Test connection with shorter timeout for faster fallback
            await asyncio.wait_for(
                client.admin.command('ping'), 
                timeout=10.0
            )
            logger.info(f"✅ Successfully connected via {attempt_name}")
            return client
            
        except (ServerSelectionTimeoutError, AutoReconnect, asyncio.TimeoutError) as e:
            logger.warning(f"❌ {attempt_name} failed: {str(e)[:100]}...")
            try:
                client.close()
            except:
                pass
            continue
        except Exception as e:
            logger.warning(f"❌ {attempt_name} failed with unexpected error: {str(e)[:100]}...")
            try:
                client.close()
            except:
                pass
            continue
    
    raise ConnectionError("All MongoDB connection attempts failed")

def create_fallback_client():
    """Create MongoDB client with alternative SSL settings"""
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.config import settings
    import urllib.parse
    import ssl
    
    if not (settings.MONGODB_USERNAME and settings.MONGODB_PASSWORD and settings.MONGODB_CLUSTER):
        raise ValueError("Atlas credentials not available")
    
    encoded_password = urllib.parse.quote_plus(settings.MONGODB_PASSWORD)
    
    # Try with standard connection without srv
    fallback_uri = (f"mongodb://{settings.MONGODB_USERNAME}:"
                   f"{encoded_password}@{settings.MONGODB_CLUSTER.replace('.mongodb.net', '.mongodb.net:27017')}/"
                   f"{settings.DATABASE_NAME}?authSource=admin&{settings.MONGODB_OPTIONS}")
    
    # Minimal SSL settings for maximum compatibility
    client_options = {
        "connectTimeoutMS": 10000,
        "socketTimeoutMS": 10000, 
        "serverSelectionTimeoutMS": 10000,
        "maxPoolSize": 5,
    }
    
    return AsyncIOMotorClient(fallback_uri, **client_options)

def create_local_client():
    """Create local MongoDB client as last resort"""
    from motor.motor_asyncio import AsyncIOMotorClient
    
    return AsyncIOMotorClient("mongodb://localhost:27017/")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with robust connection handling"""
    # Startup
    logger.info("Starting up Legal Document Search System...")
    
    # Connect with fallback strategies
    try:
        app.mongodb_client = await connect_with_fallback()
        app.mongodb = app.mongodb_client[settings.DATABASE_NAME]
        
        # Create database indexes
        await create_indexes(app.mongodb)
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        logger.error("Starting in offline mode - some features may not work")
        # Set dummy client to prevent crashes
        app.mongodb_client = None
        app.mongodb = None
    
    yield
    
    # Shutdown
    logger.info("Shutting down Legal Document Search System...")
    if hasattr(app, 'mongodb_client') and app.mongodb_client:
        app.mongodb_client.close()

# Create FastAPI application with lifespan
app = FastAPI(
    title="Legal Document Search System",
    description="AI-powered legal document digitization and search system",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(qa.router, prefix="/api/qa", tags=["qa"])

# Include new enhanced routers
app.include_router(crawling.router, prefix="/api", tags=["crawling"])
app.include_router(enhanced_processing.router, prefix="/api", tags=["document-processing"])
app.include_router(advanced_search.router, prefix="/api", tags=["advanced-search"])
app.include_router(text_analysis.router, prefix="/api", tags=["text-analysis"])
app.include_router(reports.router, prefix="/api", tags=["reports-dashboard"])

# Include chunking router
from app.routers import chunking
app.include_router(chunking.router, prefix="/api/chunks", tags=["chunking"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Legal Document Search System API",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection - use client, not database
        await app.mongodb_client.admin.command('ping')
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)