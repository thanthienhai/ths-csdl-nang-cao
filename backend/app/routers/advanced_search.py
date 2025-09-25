"""
Advanced Search Router
Endpoints for advanced search functionality
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime

from app.database import get_database
from app.models import (
    AdvancedSearchRequest, AdvancedSearchResponse, ComplexQueryRequest, 
    ComplexQueryResponse
)
from app.services.search_service import AdvancedSearchService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/advanced-search", tags=["advanced-search"])

@router.post("/", response_model=AdvancedSearchResponse)
async def advanced_search(
    request: AdvancedSearchRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Perform advanced search with various search types"""
    try:
        search_service = AdvancedSearchService(db)
        
        if request.search_type == "full_text":
            result = await search_service.full_text_search(
                query=request.query,
                filters=request.filters,
                limit=request.limit,
                offset=request.offset,
                sort_by=request.sort_by
            )
            
        elif request.search_type == "boolean":
            result = await search_service.boolean_search(
                query=request.query,
                filters=request.filters,
                limit=request.limit,
                offset=request.offset
            )
            
        elif request.search_type == "phrase":
            result = await search_service.phrase_search(
                phrase=request.query,
                filters=request.filters,
                limit=request.limit,
                offset=request.offset
            )
            
        elif request.search_type == "proximity":
            if not request.proximity_terms:
                raise HTTPException(
                    status_code=400,
                    detail="Proximity terms are required for proximity search"
                )
            result = await search_service.proximity_search(
                terms=request.proximity_terms,
                distance=request.proximity_distance,
                filters=request.filters,
                limit=request.limit,
                offset=request.offset
            )
            
        elif request.search_type == "wildcard":
            result = await search_service.wildcard_search(
                pattern=request.query,
                filters=request.filters,
                limit=request.limit,
                offset=request.offset
            )
            
        elif request.search_type == "field_specific":
            if not request.field_queries:
                raise HTTPException(
                    status_code=400,
                    detail="Field queries are required for field-specific search"
                )
            result = await search_service.field_specific_search(
                field_queries=request.field_queries,
                filters=request.filters,
                limit=request.limit,
                offset=request.offset
            )
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported search type: {request.search_type}"
            )
        
        # Convert to response model format
        response_results = []
        for item in result['results']:
            response_results.append({
                'document': item['document'],
                'score': item['score'],
                'highlights': [{'text': h} for h in item.get('highlights', [])],
                'explanation': f"Score: {item['score']:.3f}"
            })
        
        return AdvancedSearchResponse(
            results=response_results,
            total_count=result['total_count'],
            query=request.query,
            search_type=request.search_type,
            execution_time=result['execution_time'],
            suggestions=result.get('suggestions', []),
            filters_applied=request.filters
        )
        
    except Exception as e:
        logger.error(f"Advanced search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/autocomplete")
async def autocomplete(
    query: str = Query(..., min_length=1),
    field: str = Query(default="title"),
    limit: int = Query(default=10, ge=1, le=20),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get autocomplete suggestions"""
    try:
        search_service = AdvancedSearchService(db)
        suggestions = await search_service.auto_complete(query, field, limit)
        
        return {
            'query': query,
            'field': field,
            'suggestions': suggestions
        }
        
    except Exception as e:
        logger.error(f"Autocomplete failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/suggestions")
async def search_suggestions(
    query: str = Query(..., min_length=1),
    limit: int = Query(default=5, ge=1, le=10),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get search suggestions based on query"""
    try:
        search_service = AdvancedSearchService(db)
        suggestions = await search_service.search_suggestions(query, limit)
        
        return {
            'query': query,
            'suggestions': suggestions
        }
        
    except Exception as e:
        logger.error(f"Search suggestions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/complex-query", response_model=ComplexQueryResponse)
async def complex_query(
    request: ComplexQueryRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Execute complex queries with multiple conditions and facets"""
    try:
        search_service = AdvancedSearchService(db)
        
        # Build complex MongoDB query
        conditions = []
        
        for condition in request.conditions:
            field = condition.get('field')
            operator = condition.get('operator')
            value = condition.get('value')
            
            if operator == 'equals':
                conditions.append({field: value})
            elif operator == 'contains':
                conditions.append({field: {'$regex': value, '$options': 'i'}})
            elif operator == 'starts_with':
                conditions.append({field: {'$regex': f'^{value}', '$options': 'i'}})
            elif operator == 'ends_with':
                conditions.append({field: {'$regex': f'{value}$', '$options': 'i'}})
            elif operator == 'greater_than':
                conditions.append({field: {'$gt': value}})
            elif operator == 'less_than':
                conditions.append({field: {'$lt': value}})
            elif operator == 'in':
                conditions.append({field: {'$in': value}})
        
        # Combine conditions with logical operator
        if len(conditions) == 0:
            query = {}
        elif len(conditions) == 1:
            query = conditions[0]
        elif request.logical_operator == 'AND':
            query = {'$and': conditions}
        else:  # OR
            query = {'$or': conditions}
        
        # Add date range filters
        if request.date_ranges:
            for field, date_range in request.date_ranges.items():
                date_condition = {}
                if 'start' in date_range:
                    date_condition['$gte'] = date_range['start']
                if 'end' in date_range:
                    date_condition['$lte'] = date_range['end']
                
                if date_condition:
                    if '$and' in query:
                        query['$and'].append({field: date_condition})
                    else:
                        query = {'$and': [query, {field: date_condition}]}
        
        # Execute query
        cursor = db.documents.find(query)
        
        # Apply sorting
        if request.sort_criteria:
            sort_list = []
            for sort_item in request.sort_criteria:
                field = sort_item.get('field')
                direction = 1 if sort_item.get('direction', 'asc') == 'asc' else -1
                sort_list.append((field, direction))
            cursor = cursor.sort(sort_list)
        
        # Apply pagination
        cursor = cursor.skip(request.offset).limit(request.limit)
        
        # Get results
        documents = await cursor.to_list(length=request.limit)
        total_count = await db.documents.count_documents(query)
        
        # Format results
        results = []
        for doc in documents:
            results.append({
                'document': {
                    'id': str(doc.get('_id')),
                    'title': doc.get('title'),
                    'summary': doc.get('summary'),
                    'category': doc.get('category'),
                    'tags': doc.get('tags', []),
                    'date_created': doc.get('date_created'),
                    'metadata': doc.get('metadata', {})
                },
                'score': 1.0,  # Static score for complex queries
                'highlights': []
            })
        
        # Calculate facets if requested
        facets = []
        if request.facets:
            for facet_field in request.facets:
                try:
                    facet_pipeline = [
                        {'$match': query},
                        {'$group': {'_id': f'${facet_field}', 'count': {'$sum': 1}}},
                        {'$sort': {'count': -1}},
                        {'$limit': 10}
                    ]
                    
                    facet_results = await db.documents.aggregate(facet_pipeline).to_list(length=10)
                    
                    facet_values = [
                        {'value': item['_id'], 'count': item['count']}
                        for item in facet_results if item['_id']
                    ]
                    
                    facets.append({
                        'facet_name': facet_field,
                        'values': facet_values
                    })
                    
                except Exception as fe:
                    logger.warning(f"Failed to calculate facet for {facet_field}: {fe}")
        
        return ComplexQueryResponse(
            results=results,
            total_count=total_count,
            facets=facets,
            query_explanation={
                'mongodb_query': query,
                'conditions_applied': len(conditions),
                'logical_operator': request.logical_operator,
                'facets_calculated': len(facets)
            },
            execution_time=0.0  # Calculate actual execution time
        )
        
    except Exception as e:
        logger.error(f"Complex query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics")
async def get_search_analytics(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get search analytics and performance metrics"""
    try:
        search_service = AdvancedSearchService(db)
        analytics = await search_service.get_search_analytics(days)
        
        return analytics
        
    except Exception as e:
        logger.error(f"Search analytics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/popular-queries")
async def get_popular_queries(
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get popular search queries"""
    try:
        search_service = AdvancedSearchService(db)
        
        # Get analytics for the period
        analytics = await search_service.get_search_analytics(days)
        popular_queries = analytics.get('popular_queries', [])[:limit]
        
        return {
            'period_days': days,
            'popular_queries': popular_queries
        }
        
    except Exception as e:
        logger.error(f"Popular queries retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/initialize-indexes")
async def initialize_search_indexes(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Initialize search indexes for optimal performance"""
    try:
        search_service = AdvancedSearchService(db)
        await search_service.initialize_indexes()
        
        return {
            'status': 'success',
            'message': 'Search indexes initialized successfully'
        }
        
    except Exception as e:
        logger.error(f"Index initialization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))