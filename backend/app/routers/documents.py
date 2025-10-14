from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
from datetime import datetime
import logging
from bson import ObjectId
import os
from fastapi.responses import FileResponse, StreamingResponse

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
            "metadata": document.metadata
        }
        
        # Insert document
        result = await db.documents.insert_one(document_data)
        
        # Auto-create chunks for the document
        try:
            from app.services.chunking_service import chunking_service
            from app.models import ChunkingRequest
            
            chunk_request = ChunkingRequest(
                document_id=str(result.inserted_id),
                chunk_size=1000,
                chunk_overlap=200,
                chunk_strategy="recursive"
            )
            
            await chunking_service.create_chunks_for_document(
                db, str(result.inserted_id), chunk_request
            )
            logger.info(f"Auto-created chunks for document {result.inserted_id}")
        except Exception as e:
            logger.warning(f"Failed to auto-create chunks for document {result.inserted_id}: {e}")
            # Don't fail the upload if chunking fails
        
        # Retrieve and return the created document
        created_document = await db.documents.find_one({"_id": result.inserted_id})
        return DocumentModel.from_mongo(created_document)

    except Exception as e:
        logger.error(f"Failed to create document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload", response_model=DocumentModel)
async def upload_document(
    title: str = Form(...),
    category: str = Form(...),
    tags: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Upload and process a document file"""
    try:
        # Save original file
        upload_dir = os.path.join(os.path.dirname(__file__), '../../uploads')
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())
        # Re-read file for processing
        with open(file_path, "rb") as f:
            file_content = f.read()
        # Process the uploaded file
        extracted_text, file_type = await document_processor.process_uploaded_file(
            file_content, file.filename
        )
        # Generate summary
        summary = document_processor.generate_summary(extracted_text)
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
            "file_path": file_path,
            "file_size": len(file_content),
            "file_type": file_type,
            "metadata": {
                "original_filename": file.filename,
                "file_size_bytes": len(file_content)
            }
        }
        # Insert document
        result = await db.documents.insert_one(document_data)
        
        # Auto-create chunks for the uploaded document
        try:
            from app.services.chunking_service import chunking_service
            from app.models import ChunkingRequest
            
            chunk_request = ChunkingRequest(
                document_id=str(result.inserted_id),
                chunk_size=1000,
                chunk_overlap=200,
                chunk_strategy="recursive"
            )
            
            await chunking_service.create_chunks_for_document(
                db, str(result.inserted_id), chunk_request
            )
            logger.info(f"Auto-created chunks for uploaded document {result.inserted_id}")
        except Exception as e:
            logger.warning(f"Failed to auto-create chunks for uploaded document {result.inserted_id}: {e}")
            # Don't fail the upload if chunking fails
        
        # Retrieve and return the created document
        created_document = await db.documents.find_one({"_id": result.inserted_id})
        return DocumentModel.from_mongo(created_document)
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
        # Convert _id to str for each document and use from_mongo
        valid_documents = []
        for doc in documents:
            try:
                valid_documents.append(DocumentModel.from_mongo(doc))
            except Exception as e:
                logger.error(f"Invalid document skipped: {e}, doc: {doc}")
        return valid_documents

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
        return DocumentModel.from_mongo(document)

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

@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Download the original document file if available, else extracted text"""
    try:
        if not ObjectId.is_valid(document_id):
            logger.error(f"Invalid document ID for download: {document_id}")
            raise HTTPException(status_code=400, detail="Invalid document ID")
        document = await db.documents.find_one({"_id": ObjectId(document_id)})
        if not document:
            logger.error(f"Document not found for download: {document_id}")
            raise HTTPException(status_code=404, detail="Document not found")
        file_path = document.get("file_path")
        if file_path and os.path.exists(file_path):
            # Get original filename and file type from metadata
            metadata = document.get("metadata", {})
            original_filename = metadata.get("original_filename", os.path.basename(file_path))
            file_type = document.get("file_type", None)
            return FileResponse(
                file_path,
                filename=original_filename,
                media_type=file_type if file_type else "application/octet-stream"
            )
        else:
            content = document.get("content", "")
            if not content:
                logger.error(f"No file or content for document: {document_id}")
                raise HTTPException(status_code=404, detail="No file or content available")
            import io
            return StreamingResponse(io.BytesIO(content.encode("utf-8")),
                                     media_type="text/plain",
                                     headers={"Content-Disposition": f"attachment; filename=document_{document_id}.txt"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
