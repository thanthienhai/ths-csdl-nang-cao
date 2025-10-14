from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
import time
import logging

from app.database import get_database
from app.models import QARequest, QAResponse, DocumentModel
from app.ai_service import ai_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=QAResponse)
async def ask_question(
    qa_request: QARequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Answer questions based on legal documents using AI"""
    start_time = time.time()
    
    try:
        # Find relevant chunks for the question (using RAG)
        relevant_chunks = await find_relevant_chunks(
            db, 
            qa_request.question, 
            qa_request.context_limit,
            qa_request.category
        )
        
        if not relevant_chunks:
            execution_time = time.time() - start_time
            return QAResponse(
                question=qa_request.question,
                answer="Tôi không thể tìm thấy thông tin nào liên quan đến câu hỏi của bạn trong các tài liệu.",
                confidence=0.1,
                sources=[],
                execution_time=execution_time
            )
        
        # Extract context from chunks and create simplified chunk documents
        context_texts = []
        source_documents = []
        
        for chunk_data in relevant_chunks:
            context_texts.append(chunk_data.get("content", ""))
            
            # Create a simplified DocumentModel representing the chunk
            chunk_doc = DocumentModel(
                id=str(chunk_data.get("_id", "")),
                title=f"Chunk from: {chunk_data.get('document_title', 'Unknown Document')}",
                content=chunk_data.get("content", "")[:500] + "..." if len(chunk_data.get("content", "")) > 500 else chunk_data.get("content", ""),
                category=chunk_data.get("document_category", "unknown"),
                summary=f"Relevant chunk (score: {chunk_data.get('relevance_score', 0.5):.2f})",
                tags=[f"chunk_index_{chunk_data.get('chunk_index', 0)}"]
            )
            source_documents.append(chunk_doc)
        
        # Generate answer using AI service
        answer, confidence = await ai_service.generate_answer(
            qa_request.question, 
            context_texts
        )
        
        execution_time = time.time() - start_time
        
        return QAResponse(
            question=qa_request.question,
            answer=answer,
            confidence=confidence,
            sources=source_documents,
            execution_time=execution_time
        )
        
    except Exception as e:
        logger.error(f"Q&A failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def find_relevant_chunks(
    db: AsyncIOMotorDatabase,
    question: str,
    limit: int,
    category: str = None
) -> List[dict]:
    """Find chunks most relevant to the question using text search"""
    try:
        import re
        from bson import ObjectId
        
        # Simple keyword-based search (in production, use vector similarity)
        keywords = re.findall(r'\w+', question.lower())
        query_pattern = "|".join(keywords)
        
        # Build aggregation pipeline to join chunks with documents
        pipeline = [
            # Match chunks containing keywords
            {
                "$match": {
                    "content": {"$regex": query_pattern, "$options": "i"}
                }
            },
            # Join with documents collection to get document metadata
            {
                "$lookup": {
                    "from": "documents",
                    "let": {"doc_id": {"$toObjectId": "$document_id"}},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$_id", "$$doc_id"]}}}
                    ],
                    "as": "document"
                }
            },
            # Unwind document array
            {"$unwind": "$document"},
            # Add computed fields for easier access
            {
                "$addFields": {
                    "document_title": "$document.title",
                    "document_category": "$document.category",
                    "relevance_score": 0.7  # Fixed score for now, can be enhanced with TF-IDF later
                }
            },
            # Filter by category if specified
            *([{"$match": {"document_category": category}}] if category else []),
            # Sort by relevance score and chunk index
            {"$sort": {"relevance_score": -1, "chunk_index": 1}},
            # Limit results
            {"$limit": limit}
        ]
        
        cursor = db.document_chunks.aggregate(pipeline)
        chunks = await cursor.to_list(length=limit)
        
        return chunks
        
    except Exception as e:
        logger.error(f"Failed to find relevant chunks: {e}")
        # Fallback to empty list
        return []

async def find_relevant_documents(
    db: AsyncIOMotorDatabase,
    question: str,
    limit: int,
    category: str = None
) -> List[dict]:
    """Find documents most relevant to the question using text search only"""
    try:
        # Build base query
        query = {}
        if category:
            query["category"] = category
        
        # Try text search first
        try:
            query["$text"] = {"$search": question}
            cursor = db.documents.find(query)
            cursor.sort([("score", {"$meta": "textScore"})])
            cursor.limit(limit)
            
            documents = await cursor.to_list(length=limit)
            
            if documents:
                return documents
                
        except Exception as e:
            logger.warning(f"Text search failed: {e}")
        
        # Fallback to simple content search
        fallback_query = {}
        if category:
            fallback_query["category"] = category
            
        # Simple keyword matching in content
        question_terms = question.lower().split()
        regex_patterns = [{"content": {"$regex": term, "$options": "i"}} for term in question_terms]
        if regex_patterns:
            fallback_query["$or"] = regex_patterns
        
        cursor = db.documents.find(fallback_query)
        cursor.sort("date_created", -1)
        cursor.limit(limit)
        
        return await cursor.to_list(length=limit)
                
    except Exception as e:
        logger.error(f"Failed to find relevant documents: {e}")
        # Return empty list if all methods fail
        return []
        return await fallback_document_search(db, question, limit, category)

async def fallback_document_search(
    db: AsyncIOMotorDatabase,
    question: str,
    limit: int,
    category: str = None
) -> List[dict]:
    """Fallback document search using regex"""
    try:
        # Extract keywords from question
        keywords = question.lower().split()
        keywords = [word for word in keywords if len(word) > 3]  # Filter short words
        
        if not keywords:
            return []
        
        # Build regex query
        regex_conditions = []
        for keyword in keywords[:5]:  # Use max 5 keywords
            regex_conditions.extend([
                {"title": {"$regex": keyword, "$options": "i"}},
                {"content": {"$regex": keyword, "$options": "i"}},
                {"summary": {"$regex": keyword, "$options": "i"}}
            ])
        
        query = {"$or": regex_conditions}
        if category:
            query["category"] = category
        
        cursor = db.documents.find(query).limit(limit)
        documents = await cursor.to_list(length=limit)
        
        return documents
        
    except Exception as e:
        logger.error(f"Fallback document search failed: {e}")
        return []

@router.get("/suggestions")
async def get_question_suggestions(
    category: str = None,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get suggested questions based on document content"""
    try:
        # Get sample documents from the specified category
        query = {}
        if category:
            query["category"] = category
        
        cursor = db.documents.find(query).limit(10)
        documents = await cursor.to_list(length=10)
        
        if not documents:
            return {"suggestions": []}
        
        # Generate suggestions based on document categories and common legal questions
        suggestions = []
        
        # Add category-specific suggestions
        categories = set(doc.get("category", "") for doc in documents)
        for cat in categories:
            if cat:
                suggestions.extend(get_category_suggestions(cat))
        
        # Add general legal questions
        suggestions.extend([
            "Quy định về hợp đồng lao động là gì?",
            "Thời hiệu khởi kiện trong các vụ việc dân sự?",
            "Quyền và nghĩa vụ của người lao động?",
            "Quy trình giải quyết tranh chấp lao động?",
            "Các loại hình doanh nghiệp theo pháp luật Việt Nam?",
        ])
        
        # Remove duplicates and limit results
        unique_suggestions = list(set(suggestions))[:10]
        
        return {"suggestions": unique_suggestions}
        
    except Exception as e:
        logger.error(f"Failed to get question suggestions: {e}")
        return {"suggestions": []}

def get_category_suggestions(category: str) -> List[str]:
    """Get category-specific question suggestions"""
    category_lower = category.lower()
    
    suggestions_map = {
        "lao động": [
            "Quy định về thời gian làm việc?",
            "Chế độ nghỉ phép của người lao động?",
            "Quy trình chấm dứt hợp đồng lao động?",
        ],
        "dân sự": [
            "Thời hiệu khởi kiện trong các vụ việc dân sự?",
            "Quy định về quyền sở hữu tài sản?",
            "Các loại hợp đồng trong luật dân sự?",
        ],
        "hình sự": [
            "Các tình tiết tăng nặng trong luật hình sự?",
            "Quy định về bảo lãnh trong tố tụng hình sự?",
            "Thời hiệu truy cứu trách nhiệm hình sự?",
        ],
        "hành chính": [
            "Quy trình giải quyết khiếu nại hành chính?",
            "Thẩm quyền của các cơ quan hành chính?",
            "Quy định về cấp phép trong luật hành chính?",
        ],
        "thương mại": [
            "Quy định về đăng ký kinh doanh?",
            "Các loại hình công ty theo luật doanh nghiệp?",
            "Quy trình giải quyết tranh chấp thương mại?",
        ]
    }
    
    for key, suggestions in suggestions_map.items():
        if key in category_lower:
            return suggestions
    
    return []