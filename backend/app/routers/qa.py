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
        # Find relevant documents for the question
        relevant_docs = await find_relevant_documents(
            db, 
            qa_request.question, 
            qa_request.context_limit,
            qa_request.category
        )
        
        if not relevant_docs:
            execution_time = time.time() - start_time
            return QAResponse(
                question=qa_request.question,
                answer="Tôi không thể tìm thấy tài liệu nào liên quan đến câu hỏi của bạn.",
                confidence=0.1,
                sources=[],
                execution_time=execution_time
            )
        
        # Extract text content from documents
        context_texts = []
        source_documents = []
        
        for doc in relevant_docs:
            document_model = DocumentModel(**doc)
            context_texts.append(doc.get("content", ""))
            source_documents.append(document_model)
        
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

async def find_relevant_documents(
    db: AsyncIOMotorDatabase,
    question: str,
    limit: int,
    category: str = None
) -> List[dict]:
    """Find documents most relevant to the question"""
    try:
        # Generate embedding for the question
        question_embedding = ai_service.generate_embedding(question)
        
        # Build base query
        query = {}
        if category:
            query["category"] = category
        
        # Try text search first
        try:
            text_pipeline = [
                {"$match": {**query, "$text": {"$search": question}}},
                {"$addFields": {"score": {"$meta": "textScore"}}},
                {"$sort": {"score": {"$meta": "textScore"}}},
                {"$limit": limit}
            ]
            
            cursor = db.documents.aggregate(text_pipeline)
            documents = await cursor.to_list(length=limit)
            
            if documents:
                return documents
                
        except Exception as e:
            logger.warning(f"Text search failed, falling back to semantic search: {e}")
        
        # Fallback to semantic search
        cursor = db.documents.find(query)
        all_documents = await cursor.to_list(length=None)
        
        # Calculate semantic similarities
        scored_documents = []
        for doc in all_documents:
            if doc.get("vector_embedding"):
                similarity = ai_service.calculate_similarity(
                    question_embedding, 
                    doc["vector_embedding"]
                )
                scored_documents.append((doc, similarity))
        
        # Sort by similarity and take top results
        scored_documents.sort(key=lambda x: x[1], reverse=True)
        relevant_docs = [doc for doc, score in scored_documents[:limit] if score > 0.3]
        
        return relevant_docs
        
    except Exception as e:
        logger.error(f"Failed to find relevant documents: {e}")
        # Fallback to simple keyword search
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