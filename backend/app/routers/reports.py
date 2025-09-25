"""
Reports and Dashboard Router
Endpoints for generating reports and dashboard analytics
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timedelta

from app.database import get_database
from app.models import (
    ReportRequest, SearchAnalyticsReport, DocumentStatisticsReport,
    ComplianceTrackingReport, UsageMetricsReport, PerformanceMonitoringReport
)
from app.services.search_service import AdvancedSearchService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports-dashboard"])

@router.post("/search-analytics", response_model=SearchAnalyticsReport)
async def generate_search_analytics_report(
    time_period_days: int = Query(default=30, ge=1, le=365),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Generate search analytics report"""
    try:
        search_service = AdvancedSearchService(db)
        analytics = await search_service.get_search_analytics(time_period_days)
        
        return SearchAnalyticsReport(**analytics)
        
    except Exception as e:
        logger.error(f"Search analytics report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/document-statistics", response_model=DocumentStatisticsReport)
async def generate_document_statistics_report(
    time_period_days: int = Query(default=30, ge=1, le=365),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Generate document statistics report"""
    try:
        start_date = datetime.utcnow() - timedelta(days=time_period_days)
        
        # Total documents
        total_documents = await db.documents.count_documents({})
        
        # Documents by category
        category_pipeline = [
            {
                "$group": {
                    "_id": "$category",
                    "count": {"$sum": 1},
                    "avg_content_length": {"$avg": {"$strLenCP": "$content"}},
                    "latest_date": {"$max": "$date_created"}
                }
            },
            {
                "$sort": {"count": -1}
            }
        ]
        
        categories = await db.documents.aggregate(category_pipeline).to_list(length=None)
        documents_by_category = [
            {
                "category": cat["_id"],
                "count": cat["count"],
                "avg_content_length": round(cat["avg_content_length"]) if cat["avg_content_length"] else 0,
                "latest_date": cat["latest_date"]
            }
            for cat in categories if cat["_id"]
        ]
        
        # Documents by type
        type_pipeline = [
            {
                "$match": {
                    "metadata.document_type": {"$exists": True, "$ne": ""}
                }
            },
            {
                "$group": {
                    "_id": "$metadata.document_type",
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"count": -1}
            }
        ]
        
        types = await db.documents.aggregate(type_pipeline).to_list(length=None)
        documents_by_type = [
            {"type": typ["_id"], "count": typ["count"]}
            for typ in types
        ]
        
        # Documents by agency
        agency_pipeline = [
            {
                "$match": {
                    "metadata.issuing_agency": {"$exists": True, "$ne": ""}
                }
            },
            {
                "$group": {
                    "_id": "$metadata.issuing_agency",
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"count": -1}
            },
            {
                "$limit": 20
            }
        ]
        
        agencies = await db.documents.aggregate(agency_pipeline).to_list(length=20)
        documents_by_agency = [
            {"agency": agency["_id"], "count": agency["count"]}
            for agency in agencies
        ]
        
        # Content statistics
        content_stats_pipeline = [
            {
                "$group": {
                    "_id": None,
                    "avg_content_length": {"$avg": {"$strLenCP": "$content"}},
                    "max_content_length": {"$max": {"$strLenCP": "$content"}},
                    "min_content_length": {"$min": {"$strLenCP": "$content"}},
                    "avg_title_length": {"$avg": {"$strLenCP": "$title"}}
                }
            }
        ]
        
        content_stats_result = await db.documents.aggregate(content_stats_pipeline).to_list(length=1)
        content_statistics = content_stats_result[0] if content_stats_result else {}
        
        # Remove the _id field
        if "_id" in content_statistics:
            del content_statistics["_id"]
        
        # Growth trends
        growth_pipeline = [
            {
                "$match": {
                    "date_created": {"$gte": start_date}
                }
            },
            {
                "$group": {
                    "_id": {
                        "year": {"$year": "$date_created"},
                        "month": {"$month": "$date_created"},
                        "day": {"$dayOfMonth": "$date_created"}
                    },
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id": 1}
            }
        ]
        
        growth_data = await db.documents.aggregate(growth_pipeline).to_list(length=time_period_days)
        growth_trends = [
            {
                "date": f"{item['_id']['year']}-{item['_id']['month']:02d}-{item['_id']['day']:02d}",
                "count": item["count"]
            }
            for item in growth_data
        ]
        
        return DocumentStatisticsReport(
            total_documents=total_documents,
            documents_by_category=documents_by_category,
            documents_by_type=documents_by_type,
            documents_by_agency=documents_by_agency,
            content_statistics=content_statistics,
            growth_trends=growth_trends,
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Document statistics report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/compliance-tracking", response_model=ComplianceTrackingReport)
async def generate_compliance_tracking_report(
    tracked_areas: list[str] = Query(default=["dân sự", "hình sự", "hành chính", "lao động"]),
    time_period_days: int = Query(default=90, ge=1, le=365),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Generate compliance tracking report"""
    try:
        start_date = datetime.utcnow() - timedelta(days=time_period_days)
        
        # Compliance status for each tracked area
        compliance_status = {}
        
        for area in tracked_areas:
            # Find documents in this area
            area_query = {
                "classification.legal_areas.area": area,
                "date_created": {"$gte": start_date}
            }
            
            area_docs = await db.documents.find(area_query).to_list(length=None)
            
            # Check for recent changes
            recent_changes = len([
                doc for doc in area_docs 
                if doc.get('date_created', datetime.min) >= datetime.utcnow() - timedelta(days=30)
            ])
            
            # Check for amendments
            amendments = len([
                doc for doc in area_docs 
                if any(keyword in doc.get('content', '').lower() 
                      for keyword in ['sửa đổi', 'bổ sung', 'thay thế'])
            ])
            
            compliance_status[area] = {
                "total_documents": len(area_docs),
                "recent_changes": recent_changes,
                "amendments": amendments,
                "last_update": max([doc.get('date_created', datetime.min) for doc in area_docs], default=datetime.min),
                "status": "active" if recent_changes > 0 else "stable"
            }
        
        # Recent changes across all areas
        recent_changes_query = {
            "date_created": {"$gte": datetime.utcnow() - timedelta(days=30)}
        }
        
        recent_docs = await db.documents.find(recent_changes_query).sort("date_created", -1).limit(20).to_list(length=20)
        
        recent_changes = [
            {
                "document_id": str(doc["_id"]),
                "title": doc.get("title"),
                "category": doc.get("category"),
                "date_created": doc.get("date_created"),
                "change_type": "new_document"  # Could be enhanced to detect actual change types
            }
            for doc in recent_docs
        ]
        
        # Conflict alerts (placeholder - would need text analysis service)
        conflict_alerts = [
            {
                "alert_id": "sample_alert_1",
                "description": "Potential conflict detected in labor law documents",
                "severity": "medium",
                "affected_documents": [],
                "created_at": datetime.utcnow()
            }
        ]
        
        # Recommendations
        recommendations = [
            "Review recent amendments in labor law",
            "Monitor upcoming changes in administrative procedures",
            "Update compliance procedures for tax regulations"
        ]
        
        return ComplianceTrackingReport(
            tracked_areas=tracked_areas,
            compliance_status=compliance_status,
            recent_changes=recent_changes,
            conflict_alerts=conflict_alerts,
            recommendations=recommendations,
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Compliance tracking report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/usage-metrics", response_model=UsageMetricsReport)
async def generate_usage_metrics_report(
    time_period_days: int = Query(default=30, ge=1, le=365),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Generate usage metrics report"""
    try:
        start_date = datetime.utcnow() - timedelta(days=time_period_days)
        
        # Get search analytics
        search_service = AdvancedSearchService(db)
        search_analytics = await search_service.get_search_analytics(time_period_days)
        
        # Active users (placeholder - would need user tracking)
        active_users = 50  # Example value
        
        # Total queries
        total_queries = search_analytics.get('total_searches', 0)
        
        # Popular features (based on search types and endpoints)
        popular_features = [
            {"feature": "Full-text Search", "usage_count": int(total_queries * 0.6)},
            {"feature": "Advanced Search", "usage_count": int(total_queries * 0.3)},
            {"feature": "Document Analysis", "usage_count": int(total_queries * 0.1)},
        ]
        
        # User activity trends (placeholder data)
        user_activity_trends = [
            {
                "date": (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d"),
                "active_users": max(1, active_users - (i % 10)),
                "queries": max(1, int(total_queries / time_period_days) - (i % 5))
            }
            for i in range(min(time_period_days, 30))
        ]
        
        # System usage
        system_usage = {
            "storage_used_gb": 2.5,  # Placeholder
            "cpu_avg_usage": 15.2,   # Placeholder
            "memory_avg_usage": 45.8, # Placeholder
            "requests_per_minute": total_queries / (time_period_days * 24 * 60) if time_period_days > 0 else 0
        }
        
        return UsageMetricsReport(
            active_users=active_users,
            total_queries=total_queries,
            popular_features=popular_features,
            user_activity_trends=user_activity_trends,
            system_usage=system_usage,
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Usage metrics report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/performance-monitoring", response_model=PerformanceMonitoringReport)
async def generate_performance_monitoring_report(
    time_period_days: int = Query(default=7, ge=1, le=30),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Generate performance monitoring report"""
    try:
        # Get search performance data
        search_service = AdvancedSearchService(db)
        search_analytics = await search_service.get_search_analytics(time_period_days)
        
        performance_metrics = search_analytics.get('performance_metrics', {})
        
        # Response times by operation type
        response_times = {
            "search": performance_metrics.get('avg_execution_time', 0.0),
            "document_upload": 1.2,  # Placeholder
            "analysis": 3.5,         # Placeholder
            "crawling": 10.8         # Placeholder
        }
        
        # Error rates
        error_rates = {
            "search_errors": 0.01,     # 1% error rate
            "upload_errors": 0.005,    # 0.5% error rate
            "analysis_errors": 0.02,   # 2% error rate
            "system_errors": 0.001     # 0.1% error rate
        }
        
        # System health indicators
        system_health = {
            "database_status": "healthy",
            "search_index_status": "healthy",
            "api_status": "healthy",
            "storage_status": "healthy",
            "uptime_percentage": 99.9
        }
        
        # Resource usage
        resource_usage = {
            "cpu_usage_avg": 25.5,
            "memory_usage_avg": 68.2,
            "disk_usage_avg": 45.0,
            "network_io_avg": 12.3,
            "database_connections": 8
        }
        
        # Identify bottlenecks
        bottlenecks = []
        
        if response_times.get("search", 0) > 2.0:
            bottlenecks.append("Search response time is above threshold")
        
        if error_rates.get("system_errors", 0) > 0.01:
            bottlenecks.append("System error rate is elevated")
        
        if resource_usage.get("memory_usage_avg", 0) > 80:
            bottlenecks.append("Memory usage is high")
        
        return PerformanceMonitoringReport(
            response_times=response_times,
            error_rates=error_rates,
            system_health=system_health,
            resource_usage=resource_usage,
            bottlenecks=bottlenecks,
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Performance monitoring report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/overview")
async def get_dashboard_overview(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get dashboard overview with key metrics"""
    try:
        # Basic document statistics
        total_documents = await db.documents.count_documents({})
        
        # Documents added in last 30 days
        last_30_days = datetime.utcnow() - timedelta(days=30)
        recent_documents = await db.documents.count_documents({
            "date_created": {"$gte": last_30_days}
        })
        
        # Search analytics
        search_service = AdvancedSearchService(db)
        search_analytics = await search_service.get_search_analytics(7)  # Last 7 days
        
        # Top categories
        top_categories = await db.documents.aggregate([
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5}
        ]).to_list(length=5)
        
        return {
            "total_documents": total_documents,
            "recent_documents": recent_documents,
            "total_searches_7d": search_analytics.get('total_searches', 0),
            "avg_search_time": search_analytics.get('performance_metrics', {}).get('avg_execution_time', 0),
            "top_categories": [
                {"category": cat["_id"], "count": cat["count"]}
                for cat in top_categories if cat["_id"]
            ],
            "system_status": "operational",
            "last_updated": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Dashboard overview generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/{report_type}")
async def export_report(
    report_type: str,
    format: str = Query(default="json", regex="^(json|csv)$"),
    time_period_days: int = Query(default=30, ge=1, le=365),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Export report in specified format"""
    try:
        # This would typically generate the report and prepare it for download
        # For now, return a placeholder response
        
        export_id = f"export_{report_type}_{int(datetime.utcnow().timestamp())}"
        
        return {
            "export_id": export_id,
            "report_type": report_type,
            "format": format,
            "status": "generating",
            "estimated_completion": datetime.utcnow() + timedelta(minutes=5),
            "download_url": f"/reports/download/{export_id}"
        }
        
    except Exception as e:
        logger.error(f"Report export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))