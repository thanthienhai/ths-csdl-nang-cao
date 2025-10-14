from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
import logging

from app.database import get_database
from app.models import (
    DocumentChunk, 
    ChunkingRequest, 
    ChunkingResponse,
    RAGQueryRequest,
    RAGQueryResponse
)
from app.services.chunking_service import chunking_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/chunk-document", response_model=ChunkingResponse)
async def chunk_document(
    request: ChunkingRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Create chunks for a document"""
    try:
        response = await chunking_service.create_chunks_for_document(
            db, request.document_id, request
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to chunk document: {e}")
        raise HTTPException(status_code=500, detail="Failed to chunk document")

@router.get("/document/{document_id}/chunks", response_model=List[DocumentChunk])
async def get_document_chunks(
    document_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get all chunks for a document"""
    try:
        chunks = await chunking_service.get_chunks_for_document(db, document_id)
        return chunks
    except Exception as e:
        logger.error(f"Failed to get chunks for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get document chunks")

@router.delete("/document/{document_id}/chunks")
async def delete_document_chunks(
    document_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Delete all chunks for a document"""
    try:
        deleted_count = await chunking_service.delete_chunks_for_document(db, document_id)
        return {"message": f"Deleted {deleted_count} chunks", "deleted_count": deleted_count}
    except Exception as e:
        logger.error(f"Failed to delete chunks for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document chunks")

@router.get("/chunks/stats")
async def get_chunks_stats(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get chunking statistics"""
    try:
        # Get total chunks count
        total_chunks = await db.document_chunks.count_documents({})
        
        # Get chunks by document
        pipeline = [
            {
                "$group": {
                    "_id": "$document_id",
                    "chunk_count": {"$sum": 1},
                    "total_chars": {"$sum": "$content_length"}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_documents": {"$sum": 1},
                    "avg_chunks_per_doc": {"$avg": "$chunk_count"},
                    "avg_chars_per_doc": {"$avg": "$total_chars"}
                }
            }
        ]
        
        stats_cursor = db.document_chunks.aggregate(pipeline)
        stats = await stats_cursor.to_list(length=1)
        
        if stats:
            return {
                "total_chunks": total_chunks,
                "total_documents_with_chunks": stats[0]["total_documents"],
                "average_chunks_per_document": round(stats[0]["avg_chunks_per_doc"], 2),
                "average_characters_per_document": round(stats[0]["avg_chars_per_doc"], 2)
            }
        else:
            return {
                "total_chunks": 0,
                "total_documents_with_chunks": 0,
                "average_chunks_per_document": 0,
                "average_characters_per_document": 0
            }
    except Exception as e:
        logger.error(f"Failed to get chunks stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get chunks statistics")

@router.post("/rag-query", response_model=RAGQueryResponse)
async def rag_query(
    request: RAGQueryRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Perform RAG query using document chunks (placeholder - needs embedding service)"""
    try:
        # This is a placeholder implementation
        # In a real implementation, you would:
        # 1. Generate embedding for the question
        # 2. Search for similar chunks using vector similarity
        # 3. Use retrieved chunks as context for LLM
        # 4. Generate answer using LLM
        
        # For now, return a simple text-based search
        from bson import ObjectId
        import re
        
        # Simple keyword-based retrieval (replace with vector search)
        keywords = re.findall(r'\w+', request.question.lower())
        query_pattern = "|".join(keywords)
        
        chunks_cursor = db.document_chunks.find({
            "content": {"$regex": query_pattern, "$options": "i"}
        }).limit(request.top_k)
        
        retrieved_chunks = []
        async for chunk_data in chunks_cursor:
            chunk = DocumentChunk.from_mongo(chunk_data)
            
            # Get document info
            doc = await db.documents.find_one({"_id": ObjectId(chunk.document_id)})
            doc_title = doc.get("title", "Unknown") if doc else "Unknown"
            doc_category = doc.get("category", "Unknown") if doc else "Unknown"
            
            from app.models import RetrievedChunk
            retrieved_chunks.append(RetrievedChunk(
                chunk=chunk,
                similarity_score=0.8,  # Placeholder score
                document_title=doc_title,
                document_category=doc_category
            ))
        
        # Generate a simple answer (replace with LLM)
        if retrieved_chunks:
            context = "\n\n".join([rc.chunk.content[:500] + "..." for rc in retrieved_chunks])
            answer = f"Based on the retrieved documents, here's what I found about '{request.question}': {context[:1000]}..."
        else:
            answer = "I couldn't find relevant information in the document chunks to answer your question."
        
        return RAGQueryResponse(
            question=request.question,
            answer=answer,
            confidence=0.7,  # Placeholder confidence
            retrieved_chunks=retrieved_chunks,
            total_chunks_searched=await db.document_chunks.count_documents({}),
            retrieval_time=0.1,  # Placeholder times
            generation_time=0.2,
            total_time=0.3
        )
        
    except Exception as e:
        logger.error(f"Failed to perform RAG query: {e}")
        raise HTTPException(status_code=500, detail="Failed to perform RAG query")