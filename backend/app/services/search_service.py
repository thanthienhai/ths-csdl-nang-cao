"""
Advanced Search Service
Service for advanced full-text search, analytics and query optimization
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import re
import math
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from pymongo import TEXT, IndexModel
import asyncio

logger = logging.getLogger(__name__)

class AdvancedSearchService:
    """Service for advanced search functionality"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.search_analytics_collection = db.search_analytics
        
    async def initialize_indexes(self):
        """Initialize search indexes"""
        try:
            # Text search index
            await self.db.documents.create_index([
                ("title", TEXT),
                ("content", TEXT),
                ("summary", TEXT),
                ("metadata.subject", TEXT)
            ], weights={
                "title": 10,
                "summary": 5,
                "content": 1,
                "metadata.subject": 3
            })
            
            # Compound indexes for filtered search
            indexes = [
                IndexModel([("category", 1), ("date_created", -1)]),
                IndexModel([("tags", 1), ("category", 1)]),
                IndexModel([("metadata.document_type", 1), ("date_created", -1)]),
                IndexModel([("metadata.issuing_agency", 1), ("date_created", -1)]),
                IndexModel([("metadata.issue_date", -1)]),
                IndexModel([("metadata.effective_date", -1)]),
                IndexModel([("content_hash", 1)]),
                IndexModel([("legal_entities.agencies", 1)]),
                IndexModel([("legal_entities.locations", 1)]),
                IndexModel([("classification.primary_category", 1)]),
                IndexModel([("classification.legal_areas.area", 1)]),
            ]
            
            await self.db.documents.create_indexes(indexes)
            logger.info("Search indexes initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize search indexes: {e}")
            raise
    
    async def full_text_search(self, query: str, filters: Optional[Dict[str, Any]] = None,
                             limit: int = 10, offset: int = 0, 
                             sort_by: str = "relevance") -> Dict[str, Any]:
        """Advanced full-text search with MongoDB Text Search"""
        try:
            start_time = datetime.utcnow()
            
            # Build MongoDB query
            search_query = {"$text": {"$search": query}}
            
            # Add filters
            if filters:
                search_query.update(self._build_filters(filters))
            
            # Build sort criteria
            sort_criteria = self._build_sort_criteria(sort_by)
            
            # Execute search
            cursor = self.db.documents.find(
                search_query,
                {"score": {"$meta": "textScore"}}
            ).sort(sort_criteria).skip(offset).limit(limit)
            
            documents = await cursor.to_list(length=limit)
            
            # Get total count
            total_count = await self.db.documents.count_documents(search_query)
            
            # Process results
            results = []
            for doc in documents:
                result = {
                    'document': self._format_document(doc),
                    'score': doc.get('score', 0),
                    'highlights': await self._generate_highlights(doc.get('content', ''), query)
                }
                results.append(result)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Log search analytics
            await self._log_search_analytics(query, filters, len(results), execution_time)
            
            return {
                'results': results,
                'total_count': total_count,
                'query': query,
                'execution_time': execution_time,
                'filters_applied': filters or {},
                'suggestions': await self._generate_suggestions(query, len(results))
            }
            
        except Exception as e:
            logger.error(f"Full-text search failed: {e}")
            raise
    
    async def boolean_search(self, query: str, filters: Optional[Dict[str, Any]] = None,
                           limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """Boolean search with AND, OR, NOT operators"""
        try:
            start_time = datetime.utcnow()
            
            # Parse boolean query
            parsed_query = self._parse_boolean_query(query)
            
            # Build MongoDB query
            search_query = self._build_boolean_mongodb_query(parsed_query)
            
            # Add filters
            if filters:
                search_query.update(self._build_filters(filters))
            
            # Execute search
            cursor = self.db.documents.find(search_query).skip(offset).limit(limit)
            documents = await cursor.to_list(length=limit)
            
            # Get total count
            total_count = await self.db.documents.count_documents(search_query)
            
            # Process results
            results = []
            for doc in documents:
                result = {
                    'document': self._format_document(doc),
                    'score': self._calculate_boolean_score(doc, parsed_query),
                    'highlights': await self._generate_highlights(doc.get('content', ''), query)
                }
                results.append(result)
            
            # Sort by score
            results.sort(key=lambda x: x['score'], reverse=True)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                'results': results,
                'total_count': total_count,
                'query': query,
                'parsed_query': parsed_query,
                'execution_time': execution_time
            }
            
        except Exception as e:
            logger.error(f"Boolean search failed: {e}")
            raise
    
    async def phrase_search(self, phrase: str, filters: Optional[Dict[str, Any]] = None,
                          limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """Exact phrase search"""
        try:
            start_time = datetime.utcnow()
            
            # MongoDB phrase search
            search_query = {"$text": {"$search": f'"{phrase}"'}}
            
            # Add filters
            if filters:
                search_query.update(self._build_filters(filters))
            
            # Execute search
            cursor = self.db.documents.find(
                search_query,
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).skip(offset).limit(limit)
            
            documents = await cursor.to_list(length=limit)
            
            # Get total count
            total_count = await self.db.documents.count_documents(search_query)
            
            # Process results
            results = []
            for doc in documents:
                result = {
                    'document': self._format_document(doc),
                    'score': doc.get('score', 0),
                    'highlights': await self._generate_phrase_highlights(doc.get('content', ''), phrase)
                }
                results.append(result)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                'results': results,
                'total_count': total_count,
                'phrase': phrase,
                'execution_time': execution_time
            }
            
        except Exception as e:
            logger.error(f"Phrase search failed: {e}")
            raise
    
    async def proximity_search(self, terms: List[str], distance: int = 10,
                             filters: Optional[Dict[str, Any]] = None,
                             limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """Search for terms within specified distance"""
        try:
            start_time = datetime.utcnow()
            
            # Build regex for proximity search
            proximity_patterns = []
            for i, term1 in enumerate(terms):
                for j, term2 in enumerate(terms):
                    if i != j:
                        # Create pattern for terms within distance
                        pattern = f"{term1}.{{0,{distance * 50}}}{term2}"
                        proximity_patterns.append(pattern)
            
            # MongoDB regex query
            regex_pattern = "|".join(proximity_patterns)
            search_query = {
                "$or": [
                    {"content": {"$regex": regex_pattern, "$options": "i"}},
                    {"title": {"$regex": regex_pattern, "$options": "i"}}
                ]
            }
            
            # Add filters
            if filters:
                search_query.update(self._build_filters(filters))
            
            # Execute search
            cursor = self.db.documents.find(search_query).skip(offset).limit(limit)
            documents = await cursor.to_list(length=limit)
            
            # Get total count
            total_count = await self.db.documents.count_documents(search_query)
            
            # Process results and calculate proximity scores
            results = []
            for doc in documents:
                score = self._calculate_proximity_score(doc, terms, distance)
                result = {
                    'document': self._format_document(doc),
                    'score': score,
                    'highlights': await self._generate_proximity_highlights(doc.get('content', ''), terms, distance)
                }
                results.append(result)
            
            # Sort by proximity score
            results.sort(key=lambda x: x['score'], reverse=True)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                'results': results,
                'total_count': total_count,
                'terms': terms,
                'distance': distance,
                'execution_time': execution_time
            }
            
        except Exception as e:
            logger.error(f"Proximity search failed: {e}")
            raise
    
    async def wildcard_search(self, pattern: str, filters: Optional[Dict[str, Any]] = None,
                            limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """Wildcard and regex search"""
        try:
            start_time = datetime.utcnow()
            
            # Convert wildcard to regex
            regex_pattern = self._wildcard_to_regex(pattern)
            
            # MongoDB regex query
            search_query = {
                "$or": [
                    {"content": {"$regex": regex_pattern, "$options": "i"}},
                    {"title": {"$regex": regex_pattern, "$options": "i"}},
                    {"summary": {"$regex": regex_pattern, "$options": "i"}}
                ]
            }
            
            # Add filters
            if filters:
                search_query.update(self._build_filters(filters))
            
            # Execute search
            cursor = self.db.documents.find(search_query).skip(offset).limit(limit)
            documents = await cursor.to_list(length=limit)
            
            # Get total count
            total_count = await self.db.documents.count_documents(search_query)
            
            # Process results
            results = []
            for doc in documents:
                result = {
                    'document': self._format_document(doc),
                    'score': self._calculate_wildcard_score(doc, pattern),
                    'highlights': await self._generate_regex_highlights(doc.get('content', ''), regex_pattern)
                }
                results.append(result)
            
            # Sort by score
            results.sort(key=lambda x: x['score'], reverse=True)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                'results': results,
                'total_count': total_count,
                'pattern': pattern,
                'regex_pattern': regex_pattern,
                'execution_time': execution_time
            }
            
        except Exception as e:
            logger.error(f"Wildcard search failed: {e}")
            raise
    
    async def field_specific_search(self, field_queries: Dict[str, str], 
                                  filters: Optional[Dict[str, Any]] = None,
                                  limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """Search specific fields"""
        try:
            start_time = datetime.utcnow()
            
            # Build field-specific query
            search_conditions = []
            
            for field, query in field_queries.items():
                if field in ['title', 'content', 'summary']:
                    # Text search on specific field
                    search_conditions.append({
                        field: {"$regex": query, "$options": "i"}
                    })
                elif field.startswith('metadata.'):
                    # Metadata field search
                    search_conditions.append({
                        field: {"$regex": query, "$options": "i"}
                    })
                elif field == 'tags':
                    # Tag search
                    search_conditions.append({
                        "tags": {"$in": [query]}
                    })
                elif field == 'category':
                    # Category search
                    search_conditions.append({
                        "category": {"$regex": query, "$options": "i"}
                    })
            
            search_query = {"$and": search_conditions} if len(search_conditions) > 1 else search_conditions[0]
            
            # Add filters
            if filters:
                if "$and" in search_query:
                    search_query["$and"].extend(self._build_filter_conditions(filters))
                else:
                    search_query = {"$and": [search_query] + self._build_filter_conditions(filters)}
            
            # Execute search
            cursor = self.db.documents.find(search_query).skip(offset).limit(limit)
            documents = await cursor.to_list(length=limit)
            
            # Get total count
            total_count = await self.db.documents.count_documents(search_query)
            
            # Process results
            results = []
            for doc in documents:
                result = {
                    'document': self._format_document(doc),
                    'score': self._calculate_field_score(doc, field_queries),
                    'highlights': await self._generate_field_highlights(doc, field_queries)
                }
                results.append(result)
            
            # Sort by score
            results.sort(key=lambda x: x['score'], reverse=True)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                'results': results,
                'total_count': total_count,
                'field_queries': field_queries,
                'execution_time': execution_time
            }
            
        except Exception as e:
            logger.error(f"Field-specific search failed: {e}")
            raise
    
    async def auto_complete(self, partial_query: str, field: str = "title", 
                          limit: int = 10) -> List[str]:
        """Auto-complete suggestions"""
        try:
            # Build regex for auto-complete
            regex_pattern = f"^{re.escape(partial_query)}"
            
            # Aggregate to get unique suggestions
            pipeline = [
                {
                    "$match": {
                        field: {"$regex": regex_pattern, "$options": "i"}
                    }
                },
                {
                    "$group": {
                        "_id": f"${field}",
                        "count": {"$sum": 1}
                    }
                },
                {
                    "$sort": {"count": -1}
                },
                {
                    "$limit": limit
                }
            ]
            
            results = await self.db.documents.aggregate(pipeline).to_list(length=limit)
            suggestions = [result["_id"] for result in results if result["_id"]]
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Auto-complete failed: {e}")
            return []
    
    async def search_suggestions(self, query: str, limit: int = 5) -> List[str]:
        """Generate search suggestions based on query"""
        try:
            suggestions = []
            
            # Get suggestions from previous successful searches
            pipeline = [
                {
                    "$match": {
                        "query": {"$regex": query, "$options": "i"},
                        "result_count": {"$gt": 0}
                    }
                },
                {
                    "$group": {
                        "_id": "$query",
                        "popularity": {"$sum": "$result_count"},
                        "last_used": {"$max": "$timestamp"}
                    }
                },
                {
                    "$sort": {"popularity": -1, "last_used": -1}
                },
                {
                    "$limit": limit
                }
            ]
            
            results = await self.search_analytics_collection.aggregate(pipeline).to_list(length=limit)
            suggestions.extend([result["_id"] for result in results])
            
            # Add term-based suggestions
            terms = query.split()
            if terms:
                last_term = terms[-1]
                term_suggestions = await self.auto_complete(last_term, "content", 3)
                
                for suggestion in term_suggestions:
                    if len(suggestions) >= limit:
                        break
                    full_suggestion = " ".join(terms[:-1] + [suggestion]) if len(terms) > 1 else suggestion
                    if full_suggestion not in suggestions:
                        suggestions.append(full_suggestion)
            
            return suggestions[:limit]
            
        except Exception as e:
            logger.error(f"Search suggestions failed: {e}")
            return []
    
    async def get_search_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get search analytics and metrics"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Total searches
            total_searches = await self.search_analytics_collection.count_documents({
                "timestamp": {"$gte": start_date}
            })
            
            # Popular queries
            popular_pipeline = [
                {"$match": {"timestamp": {"$gte": start_date}}},
                {"$group": {
                    "_id": "$query",
                    "count": {"$sum": 1},
                    "avg_results": {"$avg": "$result_count"},
                    "avg_time": {"$avg": "$execution_time"}
                }},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            
            popular_queries = await self.search_analytics_collection.aggregate(popular_pipeline).to_list(length=10)
            
            # Search trends by day
            trends_pipeline = [
                {"$match": {"timestamp": {"$gte": start_date}}},
                {"$group": {
                    "_id": {
                        "year": {"$year": "$timestamp"},
                        "month": {"$month": "$timestamp"},
                        "day": {"$dayOfMonth": "$timestamp"}
                    },
                    "searches": {"$sum": 1},
                    "avg_results": {"$avg": "$result_count"},
                    "avg_time": {"$avg": "$execution_time"}
                }},
                {"$sort": {"_id": 1}}
            ]
            
            trends = await self.search_analytics_collection.aggregate(trends_pipeline).to_list(length=days)
            
            # Filter usage
            filter_pipeline = [
                {"$match": {"timestamp": {"$gte": start_date}, "filters": {"$exists": True, "$ne": {}}}},
                {"$unwind": {"path": "$filters", "preserveNullAndEmptyArrays": True}},
                {"$group": {
                    "_id": "$filters",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            
            filter_usage = await self.search_analytics_collection.aggregate(filter_pipeline).to_list(length=10)
            
            # Performance metrics
            perf_pipeline = [
                {"$match": {"timestamp": {"$gte": start_date}}},
                {"$group": {
                    "_id": None,
                    "avg_execution_time": {"$avg": "$execution_time"},
                    "max_execution_time": {"$max": "$execution_time"},
                    "min_execution_time": {"$min": "$execution_time"},
                    "avg_result_count": {"$avg": "$result_count"}
                }}
            ]
            
            perf_result = await self.search_analytics_collection.aggregate(perf_pipeline).to_list(length=1)
            performance = perf_result[0] if perf_result else {}
            
            return {
                'period_days': days,
                'total_searches': total_searches,
                'popular_queries': popular_queries,
                'search_trends': trends,
                'filter_usage': filter_usage,
                'performance_metrics': performance,
                'generated_at': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Failed to get search analytics: {e}")
            raise
    
    def _build_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Build MongoDB filters from search filters"""
        mongodb_filters = {}
        
        for key, value in filters.items():
            if key == 'category':
                mongodb_filters['category'] = value
            elif key == 'tags':
                mongodb_filters['tags'] = {'$in': value if isinstance(value, list) else [value]}
            elif key == 'date_range':
                if isinstance(value, dict) and 'start' in value and 'end' in value:
                    mongodb_filters['date_created'] = {
                        '$gte': value['start'],
                        '$lte': value['end']
                    }
            elif key == 'document_type':
                mongodb_filters['metadata.document_type'] = value
            elif key == 'issuing_agency':
                mongodb_filters['metadata.issuing_agency'] = {"$regex": value, "$options": "i"}
            elif key == 'issue_date_range':
                if isinstance(value, dict) and 'start' in value and 'end' in value:
                    mongodb_filters['metadata.issue_date'] = {
                        '$gte': value['start'],
                        '$lte': value['end']
                    }
            elif key == 'effective_date_range':
                if isinstance(value, dict) and 'start' in value and 'end' in value:
                    mongodb_filters['metadata.effective_date'] = {
                        '$gte': value['start'],
                        '$lte': value['end']
                    }
            elif key == 'legal_area':
                mongodb_filters['classification.legal_areas.area'] = value
            elif key == 'location':
                mongodb_filters['legal_entities.locations'] = {"$regex": value, "$options": "i"}
        
        return mongodb_filters
    
    def _build_filter_conditions(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build filter conditions as list for $and operations"""
        conditions = []
        mongodb_filters = self._build_filters(filters)
        
        for key, value in mongodb_filters.items():
            conditions.append({key: value})
        
        return conditions
    
    def _build_sort_criteria(self, sort_by: str) -> List[Tuple[str, int]]:
        """Build MongoDB sort criteria"""
        if sort_by == "relevance":
            return [("score", {"$meta": "textScore"})]
        elif sort_by == "date_desc":
            return [("date_created", -1)]
        elif sort_by == "date_asc":
            return [("date_created", 1)]
        elif sort_by == "title":
            return [("title", 1)]
        elif sort_by == "issue_date":
            return [("metadata.issue_date", -1)]
        else:
            return [("score", {"$meta": "textScore"})]
    
    def _parse_boolean_query(self, query: str) -> Dict[str, Any]:
        """Parse boolean search query"""
        # Simple boolean query parser
        # This is a basic implementation - a full parser would be more complex
        
        query = query.strip()
        
        # Handle NOT operations
        not_terms = []
        not_matches = re.findall(r'NOT\s+(\w+)', query, re.IGNORECASE)
        for term in not_matches:
            not_terms.append(term)
            query = re.sub(f'NOT\\s+{re.escape(term)}', '', query, flags=re.IGNORECASE)
        
        # Handle OR operations
        or_parts = re.split(r'\s+OR\s+', query, flags=re.IGNORECASE)
        
        and_terms = []
        or_terms = []
        
        for part in or_parts:
            if ' AND ' in part.upper():
                and_parts = re.split(r'\s+AND\s+', part, flags=re.IGNORECASE)
                and_terms.extend([term.strip() for term in and_parts if term.strip()])
            else:
                or_terms.append(part.strip())
        
        return {
            'and_terms': and_terms,
            'or_terms': or_terms,
            'not_terms': not_terms
        }
    
    def _build_boolean_mongodb_query(self, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """Build MongoDB query from parsed boolean query"""
        conditions = []
        
        # AND conditions
        if parsed_query['and_terms']:
            and_conditions = []
            for term in parsed_query['and_terms']:
                and_conditions.append({
                    "$or": [
                        {"content": {"$regex": term, "$options": "i"}},
                        {"title": {"$regex": term, "$options": "i"}},
                        {"summary": {"$regex": term, "$options": "i"}}
                    ]
                })
            conditions.extend(and_conditions)
        
        # OR conditions
        if parsed_query['or_terms']:
            or_conditions = []
            for term in parsed_query['or_terms']:
                or_conditions.append({
                    "$or": [
                        {"content": {"$regex": term, "$options": "i"}},
                        {"title": {"$regex": term, "$options": "i"}},
                        {"summary": {"$regex": term, "$options": "i"}}
                    ]
                })
            if or_conditions:
                conditions.append({"$or": or_conditions})
        
        # NOT conditions
        if parsed_query['not_terms']:
            for term in parsed_query['not_terms']:
                conditions.append({
                    "$nor": [
                        {"content": {"$regex": term, "$options": "i"}},
                        {"title": {"$regex": term, "$options": "i"}},
                        {"summary": {"$regex": term, "$options": "i"}}
                    ]
                })
        
        if len(conditions) == 1:
            return conditions[0]
        elif len(conditions) > 1:
            return {"$and": conditions}
        else:
            return {}
    
    def _wildcard_to_regex(self, pattern: str) -> str:
        """Convert wildcard pattern to regex"""
        # Escape regex special characters except * and ?
        escaped = re.escape(pattern)
        
        # Convert wildcards to regex
        regex_pattern = escaped.replace(r'\*', '.*').replace(r'\?', '.')
        
        return regex_pattern
    
    def _calculate_boolean_score(self, document: Dict[str, Any], parsed_query: Dict[str, Any]) -> float:
        """Calculate relevance score for boolean search"""
        content = f"{document.get('title', '')} {document.get('content', '')} {document.get('summary', '')}".lower()
        score = 0.0
        
        # Score AND terms
        for term in parsed_query['and_terms']:
            count = content.count(term.lower())
            score += count * 2.0  # Higher weight for AND terms
        
        # Score OR terms
        for term in parsed_query['or_terms']:
            count = content.count(term.lower())
            score += count * 1.0
        
        # Penalize NOT terms (they shouldn't be present, but if they are, reduce score)
        for term in parsed_query['not_terms']:
            count = content.count(term.lower())
            score -= count * 3.0  # Heavy penalty for NOT terms
        
        return max(score, 0.0)
    
    def _calculate_proximity_score(self, document: Dict[str, Any], terms: List[str], distance: int) -> float:
        """Calculate proximity score"""
        content = document.get('content', '')
        title = document.get('title', '')
        
        # Simple proximity scoring
        score = 0.0
        text = f"{title} {content}".lower()
        
        for i, term1 in enumerate(terms):
            for j, term2 in enumerate(terms):
                if i != j:
                    # Find positions of both terms
                    term1_pos = [m.start() for m in re.finditer(re.escape(term1.lower()), text)]
                    term2_pos = [m.start() for m in re.finditer(re.escape(term2.lower()), text)]
                    
                    # Calculate minimum distance
                    min_distance = float('inf')
                    for pos1 in term1_pos:
                        for pos2 in term2_pos:
                            char_distance = abs(pos1 - pos2)
                            word_distance = len(text[min(pos1, pos2):max(pos1, pos2)].split())
                            if word_distance <= distance:
                                min_distance = min(min_distance, word_distance)
                    
                    if min_distance != float('inf'):
                        # Score based on proximity (closer = higher score)
                        proximity_score = (distance - min_distance + 1) / distance
                        score += proximity_score
        
        return score
    
    def _calculate_wildcard_score(self, document: Dict[str, Any], pattern: str) -> float:
        """Calculate wildcard search score"""
        content = f"{document.get('title', '')} {document.get('content', '')}".lower()
        
        # Count matches
        regex_pattern = self._wildcard_to_regex(pattern.lower())
        matches = len(re.findall(regex_pattern, content))
        
        # Score based on match count and document length
        doc_length = len(content.split())
        return (matches / max(doc_length / 100, 1)) * 10
    
    def _calculate_field_score(self, document: Dict[str, Any], field_queries: Dict[str, str]) -> float:
        """Calculate field-specific search score"""
        score = 0.0
        
        for field, query in field_queries.items():
            field_content = ""
            
            if field == 'title':
                field_content = document.get('title', '')
                weight = 3.0  # Higher weight for title matches
            elif field == 'content':
                field_content = document.get('content', '')
                weight = 1.0
            elif field == 'summary':
                field_content = document.get('summary', '')
                weight = 2.0
            elif field.startswith('metadata.'):
                metadata = document.get('metadata', {})
                field_name = field.replace('metadata.', '')
                field_content = str(metadata.get(field_name, ''))
                weight = 1.5
            else:
                continue
            
            # Count matches in field
            matches = len(re.findall(re.escape(query.lower()), field_content.lower()))
            score += matches * weight
        
        return score
    
    async def _generate_highlights(self, content: str, query: str) -> List[str]:
        """Generate highlighted text snippets"""
        if not content or not query:
            return []
        
        highlights = []
        query_terms = query.lower().split()
        
        # Split content into sentences
        sentences = re.split(r'[.!?]+', content)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check if sentence contains any query terms
            sentence_lower = sentence.lower()
            matches_found = any(term in sentence_lower for term in query_terms)
            
            if matches_found:
                # Highlight matching terms
                highlighted = sentence
                for term in query_terms:
                    pattern = re.compile(re.escape(term), re.IGNORECASE)
                    highlighted = pattern.sub(f"<mark>{term}</mark>", highlighted)
                
                highlights.append(highlighted)
                
                if len(highlights) >= 3:  # Limit highlights
                    break
        
        return highlights
    
    async def _generate_phrase_highlights(self, content: str, phrase: str) -> List[str]:
        """Generate highlights for exact phrase matches"""
        if not content or not phrase:
            return []
        
        highlights = []
        phrase_lower = phrase.lower()
        
        # Find phrase matches
        matches = []
        start = 0
        while True:
            pos = content.lower().find(phrase_lower, start)
            if pos == -1:
                break
            matches.append(pos)
            start = pos + 1
        
        # Generate context around matches
        for match_pos in matches[:3]:  # Limit to 3 highlights
            # Get context (50 characters before and after)
            start = max(0, match_pos - 50)
            end = min(len(content), match_pos + len(phrase) + 50)
            context = content[start:end]
            
            # Highlight the phrase
            highlighted = re.sub(
                re.escape(phrase), 
                f"<mark>{phrase}</mark>", 
                context, 
                flags=re.IGNORECASE
            )
            
            highlights.append(highlighted)
        
        return highlights
    
    async def _generate_proximity_highlights(self, content: str, terms: List[str], distance: int) -> List[str]:
        """Generate highlights for proximity search"""
        if not content or not terms:
            return []
        
        highlights = []
        content_lower = content.lower()
        
        # Find positions of all terms
        term_positions = {}
        for term in terms:
            positions = [m.start() for m in re.finditer(re.escape(term.lower()), content_lower)]
            term_positions[term] = positions
        
        # Find proximity matches
        proximity_matches = []
        for term1 in terms:
            for term2 in terms:
                if term1 != term2:
                    for pos1 in term_positions[term1]:
                        for pos2 in term_positions[term2]:
                            char_distance = abs(pos1 - pos2)
                            if char_distance <= distance * 10:  # Approximate word distance
                                start_pos = min(pos1, pos2)
                                end_pos = max(pos1, pos2) + len(max(term1, term2, key=len))
                                proximity_matches.append((start_pos, end_pos))
        
        # Generate highlights from proximity matches
        for start_pos, end_pos in proximity_matches[:3]:
            # Get context
            context_start = max(0, start_pos - 30)
            context_end = min(len(content), end_pos + 30)
            context = content[context_start:context_end]
            
            # Highlight terms
            highlighted = context
            for term in terms:
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                highlighted = pattern.sub(f"<mark>{term}</mark>", highlighted)
            
            highlights.append(highlighted)
        
        return highlights
    
    async def _generate_regex_highlights(self, content: str, regex_pattern: str) -> List[str]:
        """Generate highlights for regex matches"""
        if not content or not regex_pattern:
            return []
        
        highlights = []
        
        try:
            matches = list(re.finditer(regex_pattern, content, re.IGNORECASE))
            
            for match in matches[:3]:  # Limit to 3 highlights
                start_pos = match.start()
                end_pos = match.end()
                
                # Get context
                context_start = max(0, start_pos - 40)
                context_end = min(len(content), end_pos + 40)
                context = content[context_start:context_end]
                
                # Highlight match
                match_text = match.group(0)
                highlighted = context.replace(match_text, f"<mark>{match_text}</mark>")
                
                highlights.append(highlighted)
                
        except re.error as e:
            logger.error(f"Regex error in highlighting: {e}")
        
        return highlights
    
    async def _generate_field_highlights(self, document: Dict[str, Any], field_queries: Dict[str, str]) -> List[str]:
        """Generate highlights for field-specific search"""
        highlights = []
        
        for field, query in field_queries.items():
            field_content = ""
            
            if field == 'title':
                field_content = document.get('title', '')
            elif field == 'content':
                field_content = document.get('content', '')
            elif field == 'summary':
                field_content = document.get('summary', '')
            elif field.startswith('metadata.'):
                metadata = document.get('metadata', {})
                field_name = field.replace('metadata.', '')
                field_content = str(metadata.get(field_name, ''))
            
            if field_content and query.lower() in field_content.lower():
                # Generate highlight for this field
                highlighted = re.sub(
                    re.escape(query),
                    f"<mark>{query}</mark>",
                    field_content[:200],  # Limit length
                    flags=re.IGNORECASE
                )
                highlights.append(f"[{field}] {highlighted}")
        
        return highlights
    
    def _format_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Format document for API response"""
        return {
            'id': str(doc.get('_id')),
            'title': doc.get('title'),
            'summary': doc.get('summary'),
            'category': doc.get('category'),
            'tags': doc.get('tags', []),
            'date_created': doc.get('date_created'),
            'metadata': doc.get('metadata', {}),
            'classification': doc.get('classification', {}),
            'legal_entities': doc.get('legal_entities', {})
        }
    
    async def _log_search_analytics(self, query: str, filters: Optional[Dict[str, Any]], 
                                  result_count: int, execution_time: float):
        """Log search analytics"""
        try:
            analytics_doc = {
                'query': query,
                'filters': filters or {},
                'result_count': result_count,
                'execution_time': execution_time,
                'timestamp': datetime.utcnow(),
                'success': result_count > 0
            }
            
            await self.search_analytics_collection.insert_one(analytics_doc)
            
        except Exception as e:
            logger.error(f"Failed to log search analytics: {e}")
    
    async def _generate_suggestions(self, query: str, result_count: int) -> List[str]:
        """Generate search suggestions when results are poor"""
        if result_count > 5:  # Good results, no suggestions needed
            return []
        
        suggestions = []
        
        # If no results, suggest similar queries
        if result_count == 0:
            # Get similar successful queries
            similar_queries = await self.search_analytics_collection.find(
                {
                    "query": {"$regex": query[:3], "$options": "i"},  # Partial match
                    "result_count": {"$gt": 0}
                },
                {"query": 1, "result_count": 1}
            ).sort("result_count", -1).limit(3).to_list(length=3)
            
            suggestions.extend([doc["query"] for doc in similar_queries])
        
        # Add general suggestions
        if not suggestions:
            query_terms = query.split()
            if len(query_terms) > 1:
                # Suggest individual terms
                suggestions.extend(query_terms[:3])
        
        return suggestions[:5]