from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import Request
import logging

logger = logging.getLogger(__name__)

def get_database(request: Request) -> AsyncIOMotorDatabase:
    """Get database instance from request"""
    return request.app.mongodb

async def create_indexes(db: AsyncIOMotorDatabase):
    """Create database indexes for optimal performance"""
    try:
        # Text search index for documents
        await db.documents.create_index([
            ("title", "text"),
            ("content", "text"),
            ("summary", "text")
        ])
        
        # Index for vector search (MongoDB Atlas Vector Search compatible)
        try:
            await db.documents.create_index([("vector_embedding", "2dsphere")])
            logger.info("Created vector search index (2dsphere)")
        except Exception as e:
            logger.warning(f"Could not create 2dsphere index: {e}")
            # Fallback to regular index for local MongoDB
            await db.documents.create_index([("vector_embedding", 1)])
            logger.info("Created fallback vector index")
        
        # Index for metadata search
        await db.documents.create_index([("category", 1)])
        await db.documents.create_index([("date_created", -1)])
        await db.documents.create_index([("tags", 1)])
        
        # Compound indexes for better query performance
        await db.documents.create_index([("category", 1), ("date_created", -1)])
        await db.documents.create_index([("tags", 1), ("category", 1)])
        
        logger.info("Successfully created database indexes")
        
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")
        # Don't raise exception, as the application can still work without indexes