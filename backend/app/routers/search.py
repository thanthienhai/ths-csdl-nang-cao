from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
import time
import logging

from app.database import get_database
from app.models import SearchRequest, SearchResponse, SearchResult, DocumentModel
from app.ai_service import ai_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=SearchResponse)
async def search_documents(
    search_request: SearchRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Search documents using text and semantic search"""
    start_time = time.time()
    
    try:
        # Generate query embedding for semantic search
        query_embedding = ai_service.generate_embedding(search_request.query)
        
        # Build MongoDB aggregation pipeline
        pipeline = []
        
        # Match stage for filtering
        match_stage = {}
        if search_request.category:
            match_stage["category"] = search_request.category
        if search_request.tags:
            match_stage["tags"] = {"$in": search_request.tags}
        
        if match_stage:
            pipeline.append({"$match": match_stage})
        
        # Add text search score if query contains text
        text_search_stage = {
            "$match": {
                "$text": {"$search": search_request.query}
            }
        }
        text_score_stage = {
            "$addFields": {
                "text_score": {"$meta": "textScore"}
            }
        }
        
        # For now, use text search as primary method
        pipeline.extend([text_search_stage, text_score_stage])
        
        # Sort by text score
        pipeline.append({"$sort": {"text_score": {"$meta": "textScore"}}})
        
        # Pagination
        pipeline.extend([
            {"$skip": search_request.offset},
            {"$limit": search_request.limit}
        ])
        
        # Execute search
        cursor = db.documents.aggregate(pipeline)
        documents = await cursor.to_list(length=search_request.limit)
        
        # Calculate semantic similarity scores and prepare results
        results = []
        for doc in documents:
            document_model = DocumentModel(**doc)
            
            # Calculate semantic similarity if embedding exists
            semantic_score = 0.0
            if doc.get("vector_embedding"):
                semantic_score = ai_service.calculate_similarity(
                    query_embedding, 
                    doc["vector_embedding"]
                )
            
            # Use text score if available, otherwise use semantic score
            final_score = doc.get("text_score", semantic_score)
            
            # Generate highlights (simple implementation)
            highlights = generate_highlights(search_request.query, doc.get("content", ""))
            
            result = SearchResult(
                document=document_model,
                score=final_score,
                highlights=highlights
            )
            results.append(result)
        
        # Get total count for pagination
        total_count = await get_search_count(db, search_request)
        
        execution_time = time.time() - start_time
        
        return SearchResponse(
            results=results,
            total_count=total_count,
            query=search_request.query,
            execution_time=execution_time
        )
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        # Fallback to simple search if text search fails
        return await fallback_search(db, search_request, start_time)

@router.post("/semantic", response_model=SearchResponse)
async def semantic_search(
    search_request: SearchRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Pure semantic search using vector embeddings"""
    start_time = time.time()
    
    try:
        # Generate query embedding
        query_embedding = ai_service.generate_embedding(search_request.query)
        
        # Build base query
        query = {}
        if search_request.category:
            query["category"] = search_request.category
        if search_request.tags:
            query["tags"] = {"$in": search_request.tags}
        
        # Get all documents that match filters
        cursor = db.documents.find(query)
        all_documents = await cursor.to_list(length=None)
        
        # Calculate semantic similarities
        scored_documents = []
        for doc in all_documents:
            if doc.get("vector_embedding"):
                similarity = ai_service.calculate_similarity(
                    query_embedding, 
                    doc["vector_embedding"]
                )
                scored_documents.append((doc, similarity))
        
        # Sort by similarity score
        scored_documents.sort(key=lambda x: x[1], reverse=True)
        
        # Apply pagination
        start_idx = search_request.offset
        end_idx = start_idx + search_request.limit
        paginated_docs = scored_documents[start_idx:end_idx]
        
        # Prepare results
        results = []
        for doc, score in paginated_docs:
            document_model = DocumentModel(**doc)
            highlights = generate_highlights(search_request.query, doc.get("content", ""))
            
            result = SearchResult(
                document=document_model,
                score=score,
                highlights=highlights
            )
            results.append(result)
        
        execution_time = time.time() - start_time
        
        return SearchResponse(
            results=results,
            total_count=len(scored_documents),
            query=search_request.query,
            execution_time=execution_time
        )
        
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_search_count(db: AsyncIOMotorDatabase, search_request: SearchRequest) -> int:
    """Get total count of search results"""
    try:
        match_stage = {"$text": {"$search": search_request.query}}
        
        if search_request.category:
            match_stage["category"] = search_request.category
        if search_request.tags:
            match_stage["tags"] = {"$in": search_request.tags}
        
        count = await db.documents.count_documents(match_stage)
        return count
        
    except Exception:
        # Fallback count
        return 0

async def fallback_search(
    db: AsyncIOMotorDatabase, 
    search_request: SearchRequest, 
    start_time: float
) -> SearchResponse:
    """Fallback search using regex when text search is not available"""
    try:
        # Build regex query
        query = {
            "$or": [
                {"title": {"$regex": search_request.query, "$options": "i"}},
                {"content": {"$regex": search_request.query, "$options": "i"}},
                {"summary": {"$regex": search_request.query, "$options": "i"}}
            ]
        }
        
        # Add filters
        if search_request.category:
            query["category"] = search_request.category
        if search_request.tags:
            query["tags"] = {"$in": search_request.tags}
        
        # Execute query
        cursor = db.documents.find(query).skip(search_request.offset).limit(search_request.limit)
        documents = await cursor.to_list(length=search_request.limit)
        
        # Prepare results
        results = []
        for doc in documents:
            document_model = DocumentModel(**doc)
            highlights = generate_highlights(search_request.query, doc.get("content", ""))
            
            result = SearchResult(
                document=document_model,
                score=0.5,  # Default score for regex search
                highlights=highlights
            )
            results.append(result)
        
        # Get total count
        total_count = await db.documents.count_documents(query)
        
        execution_time = time.time() - start_time
        
        return SearchResponse(
            results=results,
            total_count=total_count,
            query=search_request.query,
            execution_time=execution_time
        )
        
    except Exception as e:
        logger.error(f"Fallback search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def generate_highlights(query: str, content: str, max_highlights: int = 3) -> List[str]:
    """Generate text highlights for search results"""
    try:
        highlights = []
        query_words = query.lower().split()
        content_lower = content.lower()
        
        # Find sentences containing query words
        sentences = content.split('.')
        for sentence in sentences[:20]:  # Check first 20 sentences
            sentence = sentence.strip()
            if len(sentence) > 20:  # Filter short sentences
                sentence_lower = sentence.lower()
                word_count = sum(1 for word in query_words if word in sentence_lower)
                
                if word_count > 0:
                    # Truncate if too long
                    if len(sentence) > 200:
                        sentence = sentence[:200] + "..."
                    highlights.append(sentence)
                    
                    if len(highlights) >= max_highlights:
                        break
        
        return highlights
        
    except Exception as e:
        logger.error(f"Failed to generate highlights: {e}")
        return []