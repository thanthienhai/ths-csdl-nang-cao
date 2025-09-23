from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
from datetime import datetime
import logging
from bson import ObjectId

from app.database import get_database
from app.models import DocumentModel, DocumentCreate, DocumentUpdate
from app.document_processor import document_processor
from app.ai_service import ai_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=DocumentModel)
async def create_document(
    document: DocumentCreate,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Create a new document"""
    try:
        # Generate vector embedding for the content
        embedding = ai_service.generate_embedding(document.content)
        
        # Generate summary if not provided
        summary = document.summary
        if not summary:
            summary = document_processor.generate_summary(document.content)
        
        # Create document data
        document_data = {
            "title": document.title,
            "content": document.content,
            "summary": summary,
            "category": document.category,
            "tags": document.tags,
            "date_created": datetime.utcnow(),
            "vector_embedding": embedding,
            "metadata": document.metadata
        }
        
        # Insert document
        result = await db.documents.insert_one(document_data)
        
        # Retrieve and return the created document
        created_document = await db.documents.find_one({"_id": result.inserted_id})
        return DocumentModel(**created_document)
        
    except Exception as e:
        logger.error(f"Failed to create document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload", response_model=DocumentModel)
async def upload_document(
    title: str,
    category: str,
    tags: Optional[str] = None,
    file: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Upload and process a document file"""
    try:
        # Read file content
        file_content = await file.read()
        
        # Process the uploaded file
        extracted_text, file_type = await document_processor.process_uploaded_file(
            file_content, file.filename
        )
        
        # Generate summary
        summary = document_processor.generate_summary(extracted_text)
        
        # Generate vector embedding
        embedding = ai_service.generate_embedding(extracted_text)
        
        # Parse tags
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        # Create document data
        document_data = {
            "title": title,
            "content": extracted_text,
            "summary": summary,
            "category": category,
            "tags": tag_list,
            "date_created": datetime.utcnow(),
            "file_path": file.filename,
            "file_size": len(file_content),
            "file_type": file_type,
            "vector_embedding": embedding,
            "metadata": {
                "original_filename": file.filename,
                "file_size_bytes": len(file_content)
            }
        }
        
        # Insert document
        result = await db.documents.insert_one(document_data)
        
        # Retrieve and return the created document
        created_document = await db.documents.find_one({"_id": result.inserted_id})
        return DocumentModel(**created_document)
        
    except Exception as e:
        logger.error(f"Failed to upload document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[DocumentModel])
async def get_documents(
    skip: int = 0,
    limit: int = 10,
    category: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get list of documents with optional filtering"""
    try:
        # Build query
        query = {}
        if category:
            query["category"] = category
        
        # Execute query
        cursor = db.documents.find(query).skip(skip).limit(limit).sort("date_created", -1)
        documents = await cursor.to_list(length=limit)
        
        return [DocumentModel(**doc) for doc in documents]
        
    except Exception as e:
        logger.error(f"Failed to get documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{document_id}", response_model=DocumentModel)
async def get_document(
    document_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get a specific document by ID"""
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(document_id):
            raise HTTPException(status_code=400, detail="Invalid document ID")
        
        # Find document
        document = await db.documents.find_one({"_id": ObjectId(document_id)})
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return DocumentModel(**document)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{document_id}", response_model=DocumentModel)
async def update_document(
    document_id: str,
    document_update: DocumentUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update a document"""
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(document_id):
            raise HTTPException(status_code=400, detail="Invalid document ID")
        
        # Build update data
        update_data = {"date_updated": datetime.utcnow()}
        
        # Add fields that are being updated
        if document_update.title is not None:
            update_data["title"] = document_update.title
        if document_update.content is not None:
            update_data["content"] = document_update.content
            # Regenerate embedding if content changed
            update_data["vector_embedding"] = ai_service.generate_embedding(document_update.content)
        if document_update.summary is not None:
            update_data["summary"] = document_update.summary
        if document_update.category is not None:
            update_data["category"] = document_update.category
        if document_update.tags is not None:
            update_data["tags"] = document_update.tags
        if document_update.metadata is not None:
            update_data["metadata"] = document_update.metadata
        
        # Update document
        result = await db.documents.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Retrieve and return updated document
        updated_document = await db.documents.find_one({"_id": ObjectId(document_id)})
        return DocumentModel(**updated_document)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Delete a document"""
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(document_id):
            raise HTTPException(status_code=400, detail="Invalid document ID")
        
        # Delete document
        result = await db.documents.delete_one({"_id": ObjectId(document_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/categories/list")
async def get_categories(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get list of all document categories"""
    try:
        categories = await db.documents.distinct("category")
        return {"categories": categories}
        
    except Exception as e:
        logger.error(f"Failed to get categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))