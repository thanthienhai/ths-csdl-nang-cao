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
        # Nếu có query, thử text search, nếu không thì lấy tất cả
        use_text_search = False
        if search_request.query:
            try:
                query["$text"] = {"$search": search_request.query}
                use_text_search = True
            except Exception as e:
                logger.error(f"Text search not available: {e}")
        cursor = db.documents.find(query)
        if use_text_search:
            try:
                cursor.sort([("score", {"$meta": "textScore"})])
            except Exception as e:
                logger.error(f"Text score sort failed: {e}")
                cursor.sort("date_created", -1)
        else:
            cursor.sort("date_created", -1)

        # Apply pagination
        cursor.skip(search_request.offset).limit(search_request.limit)
        documents = await cursor.to_list(length=search_request.limit)

        # Prepare results
        results = []
        for doc in documents:
            try:
                document_model = DocumentModel(**doc)
                score = doc.get("score", 1.0)
                highlights = generate_highlights(search_request.query or "", doc.get("content", ""))
                result = SearchResult(document=document_model, score=score, highlights=highlights)
                results.append(result)
            except Exception as e:
                logger.error(f"Invalid document skipped: {e}, doc: {doc}")
        total_count = await db.documents.count_documents(query)

        # Nếu không có text index hoặc không có kết quả, fallback về tìm kiếm thủ công trên content/title/summary
        if search_request.query and len(results) == 0:
            # Tìm kiếm thủ công nếu text search không có kết quả
            manual_query = {"category": query.get("category"), "tags": query.get("tags")}
            manual_query = {k: v for k, v in manual_query.items() if v}
            all_docs = await db.documents.find(manual_query).to_list(length=1000)
            for doc in all_docs:
                content = doc.get("content", "")
                title = doc.get("title", "")
                summary = doc.get("summary", "")
                if (search_request.query.lower() in content.lower() or
                    search_request.query.lower() in title.lower() or
                    search_request.query.lower() in summary.lower()):
                    try:
                        document_model = DocumentModel(**doc)
                        score = 1.0
                        highlights = generate_highlights(search_request.query, content)
                        result = SearchResult(document=document_model, score=score, highlights=highlights)
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Manual search: Invalid document skipped: {e}, doc: {doc}")
            total_count = len(results)

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