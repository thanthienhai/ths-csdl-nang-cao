from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
import time
import logging

from app.database import get_database
from app.models import SearchRequest, SearchResponse, SearchResult, DocumentModel

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=SearchResponse)
async def search_documents(
    search_request: SearchRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Search documents using text search only (embedding functionality removed)"""
    start_time = time.time()
    
    try:
        # Build MongoDB query
        query = {}
        
        # Add category filter
        if search_request.category:
            query["category"] = search_request.category
        
        # Add tags filter
        if search_request.tags:
            query["tags"] = {"$in": search_request.tags}
        
        # Add text search if query provided
        if search_request.query:
            query["$text"] = {"$search": search_request.query}
        
        # Execute search with sorting and pagination
        cursor = db.documents.find(query)
        
        # Sort by text score if query provided, otherwise by date
        if search_request.query:
            cursor.sort([("score", {"$meta": "textScore"})])
        else:
            cursor.sort("date_created", -1)
        
        # Apply pagination
        cursor.skip(search_request.offset).limit(search_request.limit)
        documents = await cursor.to_list(length=search_request.limit)
        
        # Prepare results
        results = []
        for doc in documents:
            document_model = DocumentModel(**doc)
            
            # Get text score or use default
            score = 1.0
            if search_request.query:
                score = doc.get("score", 1.0)
            
            # Generate simple highlights
            highlights = generate_highlights(search_request.query or "", doc.get("content", ""))
            
            result = SearchResult(
                document=document_model,
                score=score,
                highlights=highlights
            )
            results.append(result)
        
        # Get total count
        total_count = await db.documents.count_documents(query)
        
        execution_time = time.time() - start_time
        
        return SearchResponse(
            results=results,
            total_count=total_count,
            query=search_request.query or "",
            execution_time=execution_time
        )
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

def generate_highlights(query: str, content: str, max_highlights: int = 3) -> List[str]:
    """Generate simple text highlights"""
    if not query or not content:
        return []
    
    highlights = []
    query_terms = query.lower().split()
    content_lower = content.lower()
    
    # Find sentences containing query terms
    sentences = content.split('.')
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 20:  # Skip very short sentences
            continue
            
        sentence_lower = sentence.lower()
        
        # Check if sentence contains any query terms
        for term in query_terms:
            if term in sentence_lower:
                # Add some context around the sentence
                highlight = sentence[:200] + ("..." if len(sentence) > 200 else "")
                if highlight not in highlights:
                    highlights.append(highlight)
                break
        
        if len(highlights) >= max_highlights:
            break
    
    return highlights

@router.get("/categories")
async def get_search_categories(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get all available categories for search filters"""
    try:
        categories = await db.documents.distinct("category")
        return {"categories": categories}
        
    except Exception as e:
        logger.error(f"Failed to get categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to get categories")

@router.get("/tags")
async def get_search_tags(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get all available tags for search filters"""
    try:
        tags = await db.documents.distinct("tags")
        return {"tags": tags}
        
    except Exception as e:
        logger.error(f"Failed to get tags: {e}")
        raise HTTPException(status_code=500, detail="Failed to get tags")