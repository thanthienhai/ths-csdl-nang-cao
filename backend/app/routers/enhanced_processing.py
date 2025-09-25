"""
Document Processing Router
Endpoints for enhanced document processing functionality
"""

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, Dict, Any
import logging
from datetime import datetime

from app.database import get_database
from app.models import (
    DocumentProcessingRequest, DocumentProcessingResponse,
    DocumentModel, DocumentCreate
)
from app.services.document_processing_service import EnhancedDocumentProcessor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/processing", tags=["document-processing"])

@router.post("/upload", response_model=DocumentProcessingResponse)
async def upload_and_process_document(
    file: UploadFile = File(...),
    extract_metadata: bool = Form(default=True),
    detect_duplicates: bool = Form(default=True),
    create_summary: bool = Form(default=True),
    category: Optional[str] = Form(default=None),
    tags: Optional[str] = Form(default=None),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Upload and process document with enhanced features"""
    try:
        start_time = datetime.utcnow()
        
        # Read file content
        file_content = await file.read()
        
        # Initialize processor
        processor = EnhancedDocumentProcessor(db)
        
        # Process document
        processing_result = await processor.process_document(
            file_content, file.filename
        )
        
        # Check for duplicates if requested
        is_duplicate = False
        duplicate_of = None
        
        if detect_duplicates:
            duplicate_id = await processor.check_duplicate(
                processing_result['content_hash']
            )
            if duplicate_id:
                is_duplicate = True
                duplicate_of = duplicate_id
        
        # Save document if not duplicate
        document_id = None
        if not is_duplicate:
            # Parse tags
            tag_list = []
            if tags:
                tag_list = [tag.strip() for tag in tags.split(',')]
            
            # Create document
            document_data = DocumentCreate(
                title=processing_result.get('metadata', {}).get('subject') or file.filename,
                content=processing_result['content'],
                summary=processing_result.get('summary'),
                category=category or processing_result.get('classification', {}).get('primary_category', 'khác'),
                tags=tag_list,
                metadata=processing_result.get('metadata', {})
            )
            
            # Additional fields for enhanced document
            doc_dict = document_data.model_dump()
            doc_dict.update({
                'content_hash': processing_result['content_hash'],
                'file_info': processing_result['file_info'],
                'structure': processing_result.get('structure'),
                'legal_entities': processing_result.get('legal_entities'),
                'classification': processing_result.get('classification'),
                'date_created': datetime.utcnow()
            })
            
            result = await db.documents.insert_one(doc_dict)
            document_id = str(result.inserted_id)
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return DocumentProcessingResponse(
            document_id=document_id,
            processing_status="completed" if not is_duplicate else "duplicate_detected",
            extracted_metadata=processing_result.get('metadata'),
            content_hash=processing_result['content_hash'],
            is_duplicate=is_duplicate,
            duplicate_of=duplicate_of,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Document processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch-import")
async def batch_import_documents(
    files: list[UploadFile] = File(...),
    category: Optional[str] = Form(default=None),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Batch import multiple documents"""
    try:
        processor = EnhancedDocumentProcessor(db)
        
        results = []
        
        for file in files:
            try:
                file_content = await file.read()
                
                # Process document
                processing_result = await processor.process_document(
                    file_content, file.filename
                )
                
                # Check for duplicates
                duplicate_id = await processor.check_duplicate(
                    processing_result['content_hash']
                )
                
                if not duplicate_id:
                    # Save document
                    doc_dict = {
                        'title': processing_result.get('metadata', {}).get('subject') or file.filename,
                        'content': processing_result['content'],
                        'category': category or processing_result.get('classification', {}).get('primary_category', 'khác'),
                        'content_hash': processing_result['content_hash'],
                        'file_info': processing_result['file_info'],
                        'structure': processing_result.get('structure'),
                        'legal_entities': processing_result.get('legal_entities'),
                        'classification': processing_result.get('classification'),
                        'metadata': processing_result.get('metadata', {}),
                        'date_created': datetime.utcnow()
                    }
                    
                    result = await db.documents.insert_one(doc_dict)
                    document_id = str(result.inserted_id)
                    
                    results.append({
                        'filename': file.filename,
                        'status': 'success',
                        'document_id': document_id
                    })
                else:
                    results.append({
                        'filename': file.filename,
                        'status': 'duplicate',
                        'duplicate_of': duplicate_id
                    })
                    
            except Exception as e:
                results.append({
                    'filename': file.filename,
                    'status': 'error',
                    'error': str(e)
                })
        
        successful_imports = len([r for r in results if r['status'] == 'success'])
        
        return {
            'total_files': len(files),
            'successful_imports': successful_imports,
            'duplicates_detected': len([r for r in results if r['status'] == 'duplicate']),
            'errors': len([r for r in results if r['status'] == 'error']),
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Batch import failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{document_id}/create-version")
async def create_document_version(
    document_id: str,
    file: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Create a new version of an existing document"""
    try:
        processor = EnhancedDocumentProcessor(db)
        
        # Process new version
        file_content = await file.read()
        processing_result = await processor.process_document(
            file_content, file.filename
        )
        
        # Create version
        version_id = await processor.create_document_version(
            document_id, processing_result
        )
        
        return {
            'original_document_id': document_id,
            'new_version_id': version_id,
            'version_info': processing_result.get('version_info'),
            'status': 'version_created'
        }
        
    except Exception as e:
        logger.error(f"Version creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{document_id}/versions")
async def get_document_versions(
    document_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get all versions of a document"""
    try:
        # Find all versions
        versions = await db.documents.find({
            '$or': [
                {'_id': document_id},
                {'original_document_id': document_id}
            ]
        }).sort('version_info.version_number', 1).to_list(length=None)
        
        version_list = []
        for version in versions:
            version_info = {
                'id': str(version['_id']),
                'title': version.get('title'),
                'version_number': version.get('version_info', {}).get('version_number', 1),
                'date_created': version.get('date_created'),
                'changes': version.get('version_info', {}).get('changes', {}),
                'is_current': version.get('_id') == document_id
            }
            version_list.append(version_info)
        
        return {
            'document_id': document_id,
            'total_versions': len(version_list),
            'versions': version_list
        }
        
    except Exception as e:
        logger.error(f"Failed to get document versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{document_id}/structure")
async def get_document_structure(
    document_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get parsed structure of a document"""
    try:
        document = await db.documents.find_one({'_id': document_id})
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        structure = document.get('structure', {})
        
        return {
            'document_id': document_id,
            'title': document.get('title'),
            'structure': structure,
            'structure_summary': {
                'chapters': len(structure.get('chapters', [])),
                'articles': len(structure.get('articles', [])),
                'paragraphs': len(structure.get('paragraphs', [])),
                'points': len(structure.get('points', [])),
                'appendices': len(structure.get('appendices', []))
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get document structure: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{document_id}/legal-entities")
async def get_document_legal_entities(
    document_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get extracted legal entities from a document"""
    try:
        document = await db.documents.find_one({'_id': document_id})
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        legal_entities = document.get('legal_entities', {})
        
        return {
            'document_id': document_id,
            'title': document.get('title'),
            'legal_entities': legal_entities,
            'entity_counts': {
                entity_type: len(entities) 
                for entity_type, entities in legal_entities.items()
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get legal entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))