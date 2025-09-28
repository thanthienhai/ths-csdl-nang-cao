from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from bson import ObjectId

class DocumentModel(BaseModel):
    """Document model for legal documents"""
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: Optional[str] = Field(default=None, alias="_id")
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
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @classmethod
    def from_mongo(cls, data: dict):
        """Convert MongoDB document to Pydantic model"""
        if "_id" in data:
            data["_id"] = str(data["_id"])
        return cls(**data)
    
    def to_mongo(self) -> dict:
        """Convert Pydantic model to MongoDB document"""
        data = self.model_dump(by_alias=True, exclude_unset=True)
        if "_id" in data and data["_id"]:
            data["_id"] = ObjectId(data["_id"])
        elif "_id" in data and not data["_id"]:
            data.pop("_id")
        return data

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

# Enhanced models for new functionality

class CrawlingRequest(BaseModel):
    """Model for crawling requests"""
    category: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    sources: Optional[List[str]] = None
    limit: int = Field(default=100, ge=1, le=1000)

class CrawlingResponse(BaseModel):
    """Model for crawling response"""
    documents_found: int
    documents_saved: int
    sources_crawled: List[str]
    execution_time: float
    status: str

class DocumentProcessingRequest(BaseModel):
    """Model for document processing requests"""
    filename: str
    extract_metadata: bool = True
    detect_duplicates: bool = True
    create_summary: bool = True

class DocumentProcessingResponse(BaseModel):
    """Model for document processing response"""
    document_id: Optional[str]
    processing_status: str
    extracted_metadata: Optional[Dict[str, Any]]
    content_hash: Optional[str]
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None
    processing_time: float

class AdvancedSearchRequest(BaseModel):
    """Model for advanced search requests"""
    query: str = Field(..., min_length=1, max_length=1000)
    search_type: str = Field(default="full_text", regex="^(full_text|boolean|phrase|proximity|wildcard|field_specific)$")
    
    # Boolean search specific
    boolean_operators: Optional[List[str]] = None
    
    # Proximity search specific
    proximity_terms: Optional[List[str]] = None
    proximity_distance: Optional[int] = Field(default=10, ge=1, le=50)
    
    # Field-specific search
    field_queries: Optional[Dict[str, str]] = None
    
    # Filters
    filters: Optional[Dict[str, Any]] = None
    
    # Pagination and sorting
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    sort_by: str = Field(default="relevance", regex="^(relevance|date_desc|date_asc|title|issue_date)$")

class SearchHighlight(BaseModel):
    """Model for search highlights"""
    text: str
    field: Optional[str] = None
    start_position: Optional[int] = None
    end_position: Optional[int] = None

class AdvancedSearchResult(BaseModel):
    """Model for advanced search results"""
    document: DocumentModel
    score: float
    highlights: List[SearchHighlight] = Field(default_factory=list)
    explanation: Optional[str] = None

class AdvancedSearchResponse(BaseModel):
    """Model for advanced search response"""
    results: List[AdvancedSearchResult]
    total_count: int
    query: str
    search_type: str
    execution_time: float
    suggestions: List[str] = Field(default_factory=list)
    filters_applied: Optional[Dict[str, Any]] = None

class TextAnalysisRequest(BaseModel):
    """Model for text analysis requests"""
    analysis_type: str = Field(..., regex="^(document_frequency|term_frequency|citation_network|clustering|keywords|conflict_detection|timeline)$")
    
    # Common parameters
    document_id: Optional[str] = None
    category: Optional[str] = None
    time_period_days: Optional[int] = Field(default=30, ge=1, le=3650)
    
    # Analysis specific parameters
    limit: Optional[int] = Field(default=20, ge=1, le=200)
    num_clusters: Optional[int] = Field(default=10, ge=2, le=50)
    legal_area: Optional[str] = None

class DocumentFrequencyResult(BaseModel):
    """Model for document frequency analysis results"""
    time_period_days: int
    daily_frequency: List[Dict[str, Any]]
    category_frequency: List[Dict[str, Any]]
    agency_frequency: List[Dict[str, Any]]
    total_documents: int
    analysis_date: datetime

class TermFrequencyResult(BaseModel):
    """Model for term frequency analysis results"""
    category: str
    total_documents: int
    total_terms: int
    unique_terms: int
    top_by_frequency: List[List[Union[str, int]]]
    top_by_tfidf: List[List[Union[str, float]]]
    top_legal_terms: List[List[Union[str, int]]]
    analysis_date: datetime

class CitationNetworkResult(BaseModel):
    """Model for citation network analysis results"""
    total_documents: int
    documents_with_citations: int
    total_citation_relationships: int
    most_cited_documents: List[Dict[str, Any]]
    most_citing_documents: List[Dict[str, Any]]
    citation_clusters: List[Dict[str, Any]]
    analysis_date: datetime

class DocumentClusteringResult(BaseModel):
    """Model for document clustering results"""
    category: str
    total_documents: int
    num_clusters: int
    clusters: Dict[str, Dict[str, Any]]
    analysis_date: datetime

class KeywordExtractionResult(BaseModel):
    """Model for keyword extraction results"""
    document_id: Optional[str]
    category: Optional[str]
    document_count: int
    keywords: List[List[Union[str, float]]]
    legal_keywords: List[List[Union[str, float]]]
    key_phrases: List[List[Union[str, float]]]
    analysis_date: datetime

class ConflictDetectionResult(BaseModel):
    """Model for legal conflict detection results"""
    document_id: str
    document_title: str
    total_related_documents: int
    potential_conflicts: List[Dict[str, Any]]
    temporal_conflicts: List[Dict[str, Any]]
    conflict_summary: Dict[str, int]
    analysis_date: datetime

class TimelineAnalysisResult(BaseModel):
    """Model for timeline analysis results"""
    legal_area: str
    analysis_period_years: int
    total_documents: int
    yearly_breakdown: Dict[str, List[Dict[str, Any]]]
    change_patterns: List[Dict[str, Any]]
    amendments_and_revisions: List[Dict[str, Any]]
    timeline_summary: Dict[str, Any]
    analysis_date: datetime

class ComplexQueryRequest(BaseModel):
    """Model for complex query builder requests"""
    conditions: List[Dict[str, Any]]
    logical_operator: str = Field(default="AND", regex="^(AND|OR)$")
    facets: Optional[List[str]] = None
    date_ranges: Optional[Dict[str, Dict[str, datetime]]] = None
    geospatial: Optional[Dict[str, Any]] = None
    sort_criteria: List[Dict[str, Any]] = Field(default_factory=list)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

class FacetResult(BaseModel):
    """Model for facet results"""
    facet_name: str
    values: List[Dict[str, Union[str, int]]]

class ComplexQueryResponse(BaseModel):
    """Model for complex query response"""
    results: List[AdvancedSearchResult]
    total_count: int
    facets: List[FacetResult] = Field(default_factory=list)
    query_explanation: Dict[str, Any]
    execution_time: float

class ReportRequest(BaseModel):
    """Model for report generation requests"""
    report_type: str = Field(..., regex="^(search_analytics|document_statistics|compliance_tracking|usage_metrics|performance_monitoring)$")
    time_period_days: int = Field(default=30, ge=1, le=365)
    filters: Optional[Dict[str, Any]] = None
    format: str = Field(default="json", regex="^(json|csv|pdf)$")

class SearchAnalyticsReport(BaseModel):
    """Model for search analytics report"""
    period_days: int
    total_searches: int
    popular_queries: List[Dict[str, Any]]
    search_trends: List[Dict[str, Any]]
    filter_usage: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]
    generated_at: datetime

class DocumentStatisticsReport(BaseModel):
    """Model for document statistics report"""
    total_documents: int
    documents_by_category: List[Dict[str, Any]]
    documents_by_type: List[Dict[str, Any]]
    documents_by_agency: List[Dict[str, Any]]
    content_statistics: Dict[str, Any]
    growth_trends: List[Dict[str, Any]]
    generated_at: datetime

class ComplianceTrackingReport(BaseModel):
    """Model for compliance tracking report"""
    tracked_areas: List[str]
    compliance_status: Dict[str, Dict[str, Any]]
    recent_changes: List[Dict[str, Any]]
    conflict_alerts: List[Dict[str, Any]]
    recommendations: List[str]
    generated_at: datetime

class UsageMetricsReport(BaseModel):
    """Model for usage metrics report"""
    active_users: int
    total_queries: int
    popular_features: List[Dict[str, Any]]
    user_activity_trends: List[Dict[str, Any]]
    system_usage: Dict[str, Any]
    generated_at: datetime

class PerformanceMonitoringReport(BaseModel):
    """Model for performance monitoring report"""
    response_times: Dict[str, float]
    error_rates: Dict[str, float]
    system_health: Dict[str, Any]
    resource_usage: Dict[str, Any]
    bottlenecks: List[str]
    generated_at: datetime

class BatchProcessingRequest(BaseModel):
    """Model for batch processing requests"""
    operation: str = Field(..., regex="^(import|export|analyze|update|delete)$")
    file_paths: Optional[List[str]] = None
    document_ids: Optional[List[str]] = None
    processing_options: Optional[Dict[str, Any]] = None
    schedule: Optional[datetime] = None

class BatchProcessingResponse(BaseModel):
    """Model for batch processing response"""
    job_id: str
    status: str
    total_items: int
    processed_items: int
    failed_items: int
    errors: List[str] = Field(default_factory=list)
    started_at: datetime
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None