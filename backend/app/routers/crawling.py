"""
Crawling Router
Endpoints for document crawling functionality
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Dict, Any
import logging
from datetime import datetime

from app.database import get_database
from app.models import (
    CrawlingRequest, CrawlingResponse, BatchProcessingRequest, 
    BatchProcessingResponse
)
from app.services.crawling_service import CrawlingService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/crawling", tags=["crawling"])

@router.post("/documents", response_model=CrawlingResponse)
async def crawl_documents(
    request: CrawlingRequest,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Crawl legal documents from official sources"""
    try:
        async with CrawlingService(db) as crawler:
            if request.category:
                documents = await crawler.crawl_documents_by_category(
                    request.category, request.limit
                )
            elif request.start_date and request.end_date:
                documents = await crawler.crawl_documents_by_date_range(
                    request.start_date, request.end_date, request.limit
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Either category or date range must be specified"
                )
            
            # Save documents in background
            saved_count = await crawler.save_crawled_documents(documents)
            
            return CrawlingResponse(
                documents_found=len(documents),
                documents_saved=saved_count,
                sources_crawled=list(crawler.sources.keys()),
                execution_time=0.0,  # Calculate actual time
                status="completed"
            )
            
    except Exception as e:
        logger.error(f"Document crawling failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/batch", response_model=BatchProcessingResponse)
async def batch_crawl_documents(
    request: BatchProcessingRequest,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Start batch crawling job"""
    try:
        # This would typically start a background job
        # For now, return a placeholder response
        
        job_id = f"crawl_{int(datetime.utcnow().timestamp())}"
        
        return BatchProcessingResponse(
            job_id=job_id,
            status="started",
            total_items=0,
            processed_items=0,
            failed_items=0,
            started_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Batch crawling failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sources")
async def get_available_sources(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get list of available crawling sources"""
    try:
        crawler = CrawlingService(db)
        
        sources_info = []
        for source_name, source_config in crawler.sources.items():
            sources_info.append({
                "name": source_name,
                "base_url": source_config["base_url"],
                "description": f"Official legal documents from {source_name}",
                "supported_categories": [
                    "luật", "nghị định", "thông tư", "quyết định", 
                    "chỉ thị", "nghị quyết"
                ]
            })
        
        return {
            "sources": sources_info,
            "total_sources": len(sources_info)
        }
        
    except Exception as e:
        logger.error(f"Failed to get sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{job_id}")
async def get_crawling_job_status(
    job_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get status of crawling job"""
    try:
        # This would typically query a job status from database
        # For now, return a placeholder
        
        return {
            "job_id": job_id,
            "status": "completed",
            "progress": 100,
            "message": "Crawling job completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))