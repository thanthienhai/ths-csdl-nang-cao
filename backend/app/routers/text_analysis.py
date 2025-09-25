"""
Text Analysis Router
Endpoints for text analysis and document analytics
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
import logging

from app.database import get_database
from app.models import (
    TextAnalysisRequest, DocumentFrequencyResult, TermFrequencyResult,
    CitationNetworkResult, DocumentClusteringResult, KeywordExtractionResult,
    ConflictDetectionResult, TimelineAnalysisResult
)
from app.services.text_analysis_service import TextAnalysisService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["text-analysis"])

@router.post("/document-frequency", response_model=DocumentFrequencyResult)
async def analyze_document_frequency(
    time_period_days: int = Query(default=30, ge=1, le=3650),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Analyze document frequency over time"""
    try:
        analysis_service = TextAnalysisService(db)
        result = await analysis_service.analyze_document_frequency(time_period_days)
        
        return DocumentFrequencyResult(**result)
        
    except Exception as e:
        logger.error(f"Document frequency analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/term-frequency", response_model=TermFrequencyResult)
async def analyze_term_frequency(
    category: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Analyze term frequency across documents"""
    try:
        analysis_service = TextAnalysisService(db)
        result = await analysis_service.analyze_term_frequency(category, limit)
        
        return TermFrequencyResult(**result)
        
    except Exception as e:
        logger.error(f"Term frequency analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/citation-network", response_model=CitationNetworkResult)
async def build_citation_network(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Build legal citation network"""
    try:
        analysis_service = TextAnalysisService(db)
        result = await analysis_service.build_citation_network()
        
        return CitationNetworkResult(**result)
        
    except Exception as e:
        logger.error(f"Citation network analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clustering", response_model=DocumentClusteringResult)
async def cluster_documents(
    category: Optional[str] = Query(default=None),
    num_clusters: int = Query(default=10, ge=2, le=50),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Cluster documents by content similarity"""
    try:
        analysis_service = TextAnalysisService(db)
        result = await analysis_service.cluster_documents_by_similarity(
            category, num_clusters
        )
        
        return DocumentClusteringResult(**result)
        
    except Exception as e:
        logger.error(f"Document clustering failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/keywords", response_model=KeywordExtractionResult)
async def extract_keywords(
    document_id: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Extract important keywords from documents"""
    try:
        analysis_service = TextAnalysisService(db)
        result = await analysis_service.extract_keywords(document_id, category, limit)
        
        return KeywordExtractionResult(**result)
        
    except Exception as e:
        logger.error(f"Keyword extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conflicts/{document_id}", response_model=ConflictDetectionResult)
async def detect_legal_conflicts(
    document_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Detect potential conflicts with other legal documents"""
    try:
        analysis_service = TextAnalysisService(db)
        result = await analysis_service.detect_legal_conflicts(document_id)
        
        return ConflictDetectionResult(**result)
        
    except Exception as e:
        logger.error(f"Legal conflict detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/timeline", response_model=TimelineAnalysisResult)
async def analyze_timeline_changes(
    legal_area: str = Query(...),
    years_back: int = Query(default=10, ge=1, le=50),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Analyze timeline of legal changes in specific area"""
    try:
        analysis_service = TextAnalysisService(db)
        result = await analysis_service.analyze_timeline_changes(legal_area, years_back)
        
        return TimelineAnalysisResult(**result)
        
    except Exception as e:
        logger.error(f"Timeline analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/legal-areas")
async def get_available_legal_areas(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get list of available legal areas for analysis"""
    try:
        # Get unique legal areas from documents
        pipeline = [
            {"$unwind": "$classification.legal_areas"},
            {"$group": {
                "_id": "$classification.legal_areas.area",
                "document_count": {"$sum": 1},
                "avg_score": {"$avg": "$classification.legal_areas.score"}
            }},
            {"$sort": {"document_count": -1}},
            {"$limit": 50}
        ]
        
        areas = await db.documents.aggregate(pipeline).to_list(length=50)
        
        legal_areas = [
            {
                "area": area["_id"],
                "document_count": area["document_count"],
                "avg_relevance_score": area["avg_score"]
            }
            for area in areas if area["_id"]
        ]
        
        return {
            "legal_areas": legal_areas,
            "total_areas": len(legal_areas)
        }
        
    except Exception as e:
        logger.error(f"Failed to get legal areas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/categories/stats")
async def get_category_statistics(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get statistics for document categories"""
    try:
        pipeline = [
            {
                "$group": {
                    "_id": "$category",
                    "document_count": {"$sum": 1},
                    "avg_content_length": {"$avg": {"$strLenCP": "$content"}},
                    "latest_date": {"$max": "$date_created"},
                    "earliest_date": {"$min": "$date_created"}
                }
            },
            {
                "$sort": {"document_count": -1}
            }
        ]
        
        categories = await db.documents.aggregate(pipeline).to_list(length=None)
        
        category_stats = [
            {
                "category": cat["_id"],
                "document_count": cat["document_count"],
                "avg_content_length": round(cat["avg_content_length"]) if cat["avg_content_length"] else 0,
                "latest_document": cat["latest_date"],
                "earliest_document": cat["earliest_date"]
            }
            for cat in categories if cat["_id"]
        ]
        
        return {
            "categories": category_stats,
            "total_categories": len(category_stats),
            "total_documents": sum(cat["document_count"] for cat in category_stats)
        }
        
    except Exception as e:
        logger.error(f"Failed to get category statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agencies/stats")
async def get_agency_statistics(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get statistics for issuing agencies"""
    try:
        pipeline = [
            {
                "$match": {
                    "metadata.issuing_agency": {"$exists": True, "$ne": ""}
                }
            },
            {
                "$group": {
                    "_id": "$metadata.issuing_agency",
                    "document_count": {"$sum": 1},
                    "categories": {"$addToSet": "$category"},
                    "document_types": {"$addToSet": "$metadata.document_type"},
                    "latest_date": {"$max": "$metadata.issue_date"},
                    "earliest_date": {"$min": "$metadata.issue_date"}
                }
            },
            {
                "$sort": {"document_count": -1}
            },
            {
                "$limit": limit
            }
        ]
        
        agencies = await db.documents.aggregate(pipeline).to_list(length=limit)
        
        agency_stats = [
            {
                "agency": agency["_id"],
                "document_count": agency["document_count"],
                "categories_covered": len(agency["categories"]),
                "document_types": [dt for dt in agency["document_types"] if dt],
                "latest_document_date": agency["latest_date"],
                "earliest_document_date": agency["earliest_date"]
            }
            for agency in agencies
        ]
        
        return {
            "agencies": agency_stats,
            "total_agencies_shown": len(agency_stats)
        }
        
    except Exception as e:
        logger.error(f"Failed to get agency statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))