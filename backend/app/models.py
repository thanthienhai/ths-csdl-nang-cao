from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId

class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic"""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

class DocumentModel(BaseModel):
    """Document model for legal documents"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    summary: Optional[str] = None
    category: str = Field(..., min_length=1, max_length=100)
    tags: List[str] = Field(default_factory=list)
    date_created: datetime = Field(default_factory=datetime.utcnow)
    date_updated: Optional[datetime] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    vector_embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class DocumentCreate(BaseModel):
    """Model for creating new documents"""
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    summary: Optional[str] = None
    category: str = Field(..., min_length=1, max_length=100)
    tags: List[str] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class DocumentUpdate(BaseModel):
    """Model for updating existing documents"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = Field(None, min_length=1)
    summary: Optional[str] = None
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class SearchRequest(BaseModel):
    """Model for search requests"""
    query: str = Field(..., min_length=1, max_length=1000)
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    limit: Optional[int] = Field(default=10, ge=1, le=100)
    offset: Optional[int] = Field(default=0, ge=0)

class SearchResult(BaseModel):
    """Model for search results"""
    document: DocumentModel
    score: float
    highlights: Optional[List[str]] = None

class SearchResponse(BaseModel):
    """Model for search response"""
    results: List[SearchResult]
    total_count: int
    query: str
    execution_time: float

class QARequest(BaseModel):
    """Model for Q&A requests"""
    question: str = Field(..., min_length=1, max_length=1000)
    context_limit: Optional[int] = Field(default=5, ge=1, le=20)
    category: Optional[str] = None

class QAResponse(BaseModel):
    """Model for Q&A response"""
    question: str
    answer: str
    confidence: float
    sources: List[DocumentModel]
    execution_time: float