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
        
        # Index for metadata search
        await db.documents.create_index([("category", 1)])
        await db.documents.create_index([("date_created", -1)])
        await db.documents.create_index([("tags", 1)])
        
        # Compound indexes for better query performance
        await db.documents.create_index([("category", 1), ("date_created", -1)])
        await db.documents.create_index([("tags", 1), ("category", 1)])
        
        # Indexes for document chunks collection
        await db.document_chunks.create_index([("content", "text")])
        await db.document_chunks.create_index([("document_id", 1)])
        await db.document_chunks.create_index([("chunk_index", 1)])
        await db.document_chunks.create_index([("document_id", 1), ("chunk_index", 1)])
        
        # Index for embeddings if using vector search
        # await db.document_chunks.create_index([("embedding", "2dsphere")])  # For vector search
        
        logger.info("Successfully created database indexes")
        
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")
        # Don't raise exception, as the application can still work without indexes