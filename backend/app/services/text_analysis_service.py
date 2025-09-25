"""
Text Analysis Service
Service for document analysis, clustering, and legal conflict detection
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import re
import math
from collections import Counter, defaultdict
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import asyncio

logger = logging.getLogger(__name__)

class TextAnalysisService:
    """Service for advanced text analysis"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.analysis_cache = {}
        
    async def analyze_document_frequency(self, time_period: int = 30) -> Dict[str, Any]:
        """Analyze document frequency over time period"""
        try:
            start_date = datetime.utcnow() - timedelta(days=time_period)
            
            # Document frequency by day
            pipeline = [
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
                        "count": {"$sum": 1},
                        "categories": {"$push": "$category"},
                        "document_types": {"$push": "$metadata.document_type"}
                    }
                },
                {
                    "$sort": {"_id": 1}
                }
            ]
            
            daily_counts = await self.db.documents.aggregate(pipeline).to_list(length=time_period)
            
            # Document frequency by category
            category_pipeline = [
                {
                    "$match": {
                        "date_created": {"$gte": start_date}
                    }
                },
                {
                    "$group": {
                        "_id": "$category",
                        "count": {"$sum": 1},
                        "avg_content_length": {"$avg": {"$strLenCP": "$content"}},
                        "document_types": {"$push": "$metadata.document_type"}
                    }
                },
                {
                    "$sort": {"count": -1}
                }
            ]
            
            category_counts = await self.db.documents.aggregate(category_pipeline).to_list(length=50)
            
            # Document frequency by issuing agency
            agency_pipeline = [
                {
                    "$match": {
                        "date_created": {"$gte": start_date},
                        "metadata.issuing_agency": {"$exists": True, "$ne": ""}
                    }
                },
                {
                    "$group": {
                        "_id": "$metadata.issuing_agency",
                        "count": {"$sum": 1},
                        "categories": {"$addToSet": "$category"}
                    }
                },
                {
                    "$sort": {"count": -1}
                },
                {
                    "$limit": 20
                }
            ]
            
            agency_counts = await self.db.documents.aggregate(agency_pipeline).to_list(length=20)
            
            return {
                'time_period_days': time_period,
                'daily_frequency': daily_counts,
                'category_frequency': category_counts,
                'agency_frequency': agency_counts,
                'total_documents': sum(day['count'] for day in daily_counts),
                'analysis_date': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Document frequency analysis failed: {e}")
            raise
    
    async def analyze_term_frequency(self, category: Optional[str] = None, 
                                   limit: int = 100) -> Dict[str, Any]:
        """Analyze term frequency across documents"""
        try:
            # Build match query
            match_query = {}
            if category:
                match_query['category'] = category
            
            # Get all documents
            documents = await self.db.documents.find(
                match_query, 
                {'content': 1, 'title': 1, 'category': 1}
            ).to_list(length=None)
            
            # Combine all text
            all_text = ""
            term_document_count = defaultdict(set)  # Track which documents contain each term
            
            for doc in documents:
                doc_id = str(doc['_id'])
                text = f"{doc.get('title', '')} {doc.get('content', '')}"
                all_text += text.lower() + " "
                
                # Track terms per document for TF-IDF calculation
                words = self._tokenize_vietnamese_text(text.lower())
                for word in set(words):  # Use set to count each term once per document
                    term_document_count[word].add(doc_id)
            
            # Tokenize and count terms
            words = self._tokenize_vietnamese_text(all_text)
            term_counts = Counter(words)
            
            # Calculate TF-IDF scores
            total_documents = len(documents)
            tf_idf_scores = {}
            
            for term, tf in term_counts.items():
                df = len(term_document_count[term])  # Document frequency
                if df > 0:
                    idf = math.log(total_documents / df)
                    tf_idf_scores[term] = tf * idf
                else:
                    tf_idf_scores[term] = 0
            
            # Get top terms by different metrics
            top_by_frequency = term_counts.most_common(limit)
            top_by_tfidf = sorted(tf_idf_scores.items(), key=lambda x: x[1], reverse=True)[:limit]
            
            # Legal-specific terms
            legal_terms = self._extract_legal_terms(words)
            legal_term_counts = {term: term_counts[term] for term in legal_terms if term in term_counts}
            top_legal_terms = sorted(legal_term_counts.items(), key=lambda x: x[1], reverse=True)[:50]
            
            return {
                'category': category or 'all',
                'total_documents': total_documents,
                'total_terms': len(term_counts),
                'unique_terms': len(set(words)),
                'top_by_frequency': top_by_frequency,
                'top_by_tfidf': top_by_tfidf,
                'top_legal_terms': top_legal_terms,
                'analysis_date': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Term frequency analysis failed: {e}")
            raise
    
    async def build_citation_network(self) -> Dict[str, Any]:
        """Build legal citation network"""
        try:
            # Get all documents with their references
            documents = await self.db.documents.find(
                {},
                {
                    'title': 1, 
                    'content': 1, 
                    'metadata.document_number': 1,
                    'legal_entities.document_references': 1,
                    'category': 1
                }
            ).to_list(length=None)
            
            # Build citation graph
            citation_graph = defaultdict(list)
            document_map = {}  # Map document numbers to document IDs
            
            # Create document mapping
            for doc in documents:
                doc_id = str(doc['_id'])
                doc_number = doc.get('metadata', {}).get('document_number')
                if doc_number:
                    document_map[doc_number] = {
                        'id': doc_id,
                        'title': doc.get('title', ''),
                        'category': doc.get('category', '')
                    }
            
            # Extract citations
            for doc in documents:
                doc_id = str(doc['_id'])
                doc_number = doc.get('metadata', {}).get('document_number')
                
                # Get references from content
                content_refs = self._extract_document_references(doc.get('content', ''))
                
                # Get references from legal entities
                entity_refs = doc.get('legal_entities', {}).get('document_references', [])
                
                all_refs = content_refs + entity_refs
                
                # Build citation relationships
                for ref in all_refs:
                    if ref in document_map and doc_number:
                        citation_graph[doc_number].append(ref)
            
            # Calculate citation statistics
            citation_counts = {}  # How many times each document is cited
            citing_counts = {}   # How many documents each document cites
            
            for citing_doc, cited_docs in citation_graph.items():
                citing_counts[citing_doc] = len(cited_docs)
                for cited_doc in cited_docs:
                    citation_counts[cited_doc] = citation_counts.get(cited_doc, 0) + 1
            
            # Most cited documents
            most_cited = sorted(citation_counts.items(), key=lambda x: x[1], reverse=True)[:20]
            
            # Documents with most citations
            most_citing = sorted(citing_counts.items(), key=lambda x: x[1], reverse=True)[:20]
            
            # Citation clusters (documents that cite similar documents)
            clusters = self._find_citation_clusters(citation_graph)
            
            return {
                'total_documents': len(documents),
                'documents_with_citations': len(citation_graph),
                'total_citation_relationships': sum(len(refs) for refs in citation_graph.values()),
                'most_cited_documents': [
                    {
                        'document_number': doc_num,
                        'citation_count': count,
                        'document_info': document_map.get(doc_num, {})
                    }
                    for doc_num, count in most_cited
                ],
                'most_citing_documents': [
                    {
                        'document_number': doc_num,
                        'citing_count': count,
                        'document_info': document_map.get(doc_num, {})
                    }
                    for doc_num, count in most_citing
                ],
                'citation_clusters': clusters,
                'citation_graph': dict(citation_graph),  # Convert defaultdict to dict
                'analysis_date': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Citation network analysis failed: {e}")
            raise
    
    async def cluster_documents_by_similarity(self, category: Optional[str] = None,
                                            num_clusters: int = 10) -> Dict[str, Any]:
        """Cluster documents based on content similarity"""
        try:
            # Build match query
            match_query = {}
            if category:
                match_query['category'] = category
            
            # Get documents
            documents = await self.db.documents.find(
                match_query,
                {
                    'title': 1, 
                    'content': 1, 
                    'summary': 1, 
                    'category': 1,
                    'metadata': 1
                }
            ).limit(500).to_list(length=500)  # Limit for performance
            
            if len(documents) < 2:
                return {
                    'error': 'Need at least 2 documents for clustering',
                    'document_count': len(documents)
                }
            
            # Create document vectors using term frequency
            doc_vectors = {}
            all_terms = set()
            
            # Build vocabulary and document vectors
            for doc in documents:
                doc_id = str(doc['_id'])
                text = f"{doc.get('title', '')} {doc.get('content', '')} {doc.get('summary', '')}"
                terms = self._tokenize_vietnamese_text(text.lower())
                term_counts = Counter(terms)
                
                doc_vectors[doc_id] = term_counts
                all_terms.update(terms)
            
            # Convert to TF-IDF vectors
            all_terms = list(all_terms)
            tfidf_vectors = {}
            
            for doc_id, term_counts in doc_vectors.items():
                vector = []
                for term in all_terms:
                    tf = term_counts.get(term, 0)
                    df = sum(1 for doc_terms in doc_vectors.values() if term in doc_terms)
                    idf = math.log(len(documents) / max(df, 1))
                    tfidf = tf * idf
                    vector.append(tfidf)
                tfidf_vectors[doc_id] = vector
            
            # Simple K-means clustering
            clusters = self._kmeans_clustering(tfidf_vectors, num_clusters)
            
            # Analyze clusters
            cluster_analysis = {}
            for cluster_id, doc_ids in clusters.items():
                cluster_docs = [doc for doc in documents if str(doc['_id']) in doc_ids]
                
                # Find common terms in cluster
                all_cluster_text = " ".join([
                    f"{doc.get('title', '')} {doc.get('content', '')}" 
                    for doc in cluster_docs
                ])
                cluster_terms = self._tokenize_vietnamese_text(all_cluster_text.lower())
                common_terms = Counter(cluster_terms).most_common(10)
                
                # Cluster statistics
                categories = [doc.get('category') for doc in cluster_docs]
                category_dist = Counter(categories)
                
                cluster_analysis[cluster_id] = {
                    'document_count': len(cluster_docs),
                    'documents': [
                        {
                            'id': str(doc['_id']),
                            'title': doc.get('title'),
                            'category': doc.get('category')
                        }
                        for doc in cluster_docs
                    ],
                    'common_terms': common_terms,
                    'category_distribution': dict(category_dist),
                    'cluster_quality': self._calculate_cluster_quality(doc_ids, tfidf_vectors, all_terms)
                }
            
            return {
                'category': category or 'all',
                'total_documents': len(documents),
                'num_clusters': num_clusters,
                'clusters': cluster_analysis,
                'analysis_date': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Document clustering failed: {e}")
            raise
    
    async def extract_keywords(self, document_id: Optional[str] = None,
                             category: Optional[str] = None, 
                             limit: int = 20) -> Dict[str, Any]:
        """Extract important keywords from documents"""
        try:
            # Build query
            if document_id:
                match_query = {'_id': ObjectId(document_id)}
            elif category:
                match_query = {'category': category}
            else:
                match_query = {}
            
            # Get documents
            documents = await self.db.documents.find(
                match_query,
                {'title': 1, 'content': 1, 'summary': 1, 'category': 1}
            ).to_list(length=None)
            
            if not documents:
                return {'error': 'No documents found', 'keywords': []}
            
            # Combine all text
            all_text = ""
            for doc in documents:
                text = f"{doc.get('title', '')} {doc.get('content', '')} {doc.get('summary', '')}"
                all_text += text.lower() + " "
            
            # Tokenize
            terms = self._tokenize_vietnamese_text(all_text)
            
            # Calculate term importance scores
            term_scores = self._calculate_term_importance(terms, all_text)
            
            # Filter legal terms
            legal_terms = self._extract_legal_terms(terms)
            legal_scores = {term: score for term, score in term_scores.items() if term in legal_terms}
            
            # Get top keywords
            top_keywords = sorted(term_scores.items(), key=lambda x: x[1], reverse=True)[:limit]
            top_legal_keywords = sorted(legal_scores.items(), key=lambda x: x[1], reverse=True)[:limit//2]
            
            # Extract key phrases (2-3 word combinations)
            key_phrases = self._extract_key_phrases(all_text, limit//2)
            
            return {
                'document_id': document_id,
                'category': category,
                'document_count': len(documents),
                'keywords': top_keywords,
                'legal_keywords': top_legal_keywords,
                'key_phrases': key_phrases,
                'analysis_date': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            raise
    
    async def detect_legal_conflicts(self, document_id: str) -> Dict[str, Any]:
        """Detect potential conflicts with other legal documents"""
        try:
            # Get target document
            target_doc = await self.db.documents.find_one({'_id': ObjectId(document_id)})
            if not target_doc:
                return {'error': 'Document not found'}
            
            # Get related documents (same category or legal area)
            related_query = {
                '_id': {'$ne': ObjectId(document_id)},
                '$or': [
                    {'category': target_doc.get('category')},
                    {'classification.legal_areas.area': {'$in': [
                        area.get('area') for area in target_doc.get('classification', {}).get('legal_areas', [])
                    ]}}
                ]
            }
            
            related_docs = await self.db.documents.find(related_query).to_list(length=100)
            
            # Analyze conflicts
            conflicts = []
            
            target_content = target_doc.get('content', '').lower()
            target_title = target_doc.get('title', '').lower()
            
            for related_doc in related_docs:
                related_content = related_doc.get('content', '').lower()
                related_title = related_doc.get('title', '').lower()
                
                # Check for conflicting statements
                conflict_indicators = self._detect_content_conflicts(
                    target_content, related_content
                )
                
                if conflict_indicators['conflict_score'] > 0.3:  # Threshold for conflict
                    conflicts.append({
                        'document_id': str(related_doc['_id']),
                        'title': related_doc.get('title'),
                        'category': related_doc.get('category'),
                        'conflict_score': conflict_indicators['conflict_score'],
                        'conflict_type': conflict_indicators['conflict_type'],
                        'conflicting_passages': conflict_indicators['passages'],
                        'issue_date': related_doc.get('metadata', {}).get('issue_date'),
                        'document_number': related_doc.get('metadata', {}).get('document_number')
                    })
            
            # Sort by conflict score
            conflicts.sort(key=lambda x: x['conflict_score'], reverse=True)
            
            # Analyze temporal conflicts (newer vs older documents)
            temporal_conflicts = self._analyze_temporal_conflicts(target_doc, conflicts)
            
            return {
                'document_id': document_id,
                'document_title': target_doc.get('title'),
                'total_related_documents': len(related_docs),
                'potential_conflicts': conflicts[:10],  # Top 10 conflicts
                'temporal_conflicts': temporal_conflicts,
                'conflict_summary': {
                    'high_risk': len([c for c in conflicts if c['conflict_score'] > 0.7]),
                    'medium_risk': len([c for c in conflicts if 0.4 <= c['conflict_score'] <= 0.7]),
                    'low_risk': len([c for c in conflicts if 0.3 <= c['conflict_score'] < 0.4])
                },
                'analysis_date': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Legal conflict detection failed: {e}")
            raise
    
    async def analyze_timeline_changes(self, legal_area: str, 
                                     years_back: int = 10) -> Dict[str, Any]:
        """Analyze timeline of legal changes in specific area"""
        try:
            start_date = datetime.utcnow() - timedelta(days=years_back * 365)
            
            # Get documents in the legal area
            pipeline = [
                {
                    "$match": {
                        "classification.legal_areas.area": legal_area,
                        "metadata.issue_date": {"$gte": start_date}
                    }
                },
                {
                    "$sort": {"metadata.issue_date": 1}
                }
            ]
            
            documents = await self.db.documents.aggregate(pipeline).to_list(length=None)
            
            if not documents:
                return {'error': f'No documents found for legal area: {legal_area}'}
            
            # Group by year
            yearly_changes = defaultdict(list)
            
            for doc in documents:
                issue_date = doc.get('metadata', {}).get('issue_date')
                if issue_date:
                    year = issue_date.year
                    yearly_changes[year].append({
                        'id': str(doc['_id']),
                        'title': doc.get('title'),
                        'document_type': doc.get('metadata', {}).get('document_type'),
                        'document_number': doc.get('metadata', {}).get('document_number'),
                        'issue_date': issue_date,
                        'issuing_agency': doc.get('metadata', {}).get('issuing_agency'),
                        'summary_keywords': self._extract_change_keywords(doc.get('content', ''))
                    })
            
            # Analyze change patterns
            change_patterns = []
            
            # Detect major change periods
            for year, docs in yearly_changes.items():
                if len(docs) > len(documents) / years_back * 2:  # Above average activity
                    change_patterns.append({
                        'year': year,
                        'document_count': len(docs),
                        'change_type': 'high_activity',
                        'description': f'High regulatory activity with {len(docs)} documents'
                    })
            
            # Detect amendments and revisions
            amendments = []
            for doc in documents:
                content = doc.get('content', '').lower()
                if any(keyword in content for keyword in ['sửa đổi', 'bổ sung', 'thay thế', 'bãi bỏ']):
                    amendments.append({
                        'id': str(doc['_id']),
                        'title': doc.get('title'),
                        'issue_date': doc.get('metadata', {}).get('issue_date'),
                        'amendment_type': self._classify_amendment(content)
                    })
            
            return {
                'legal_area': legal_area,
                'analysis_period_years': years_back,
                'total_documents': len(documents),
                'yearly_breakdown': dict(yearly_changes),
                'change_patterns': change_patterns,
                'amendments_and_revisions': amendments,
                'timeline_summary': {
                    'most_active_year': max(yearly_changes.keys(), key=lambda y: len(yearly_changes[y])) if yearly_changes else None,
                    'least_active_year': min(yearly_changes.keys(), key=lambda y: len(yearly_changes[y])) if yearly_changes else None,
                    'average_documents_per_year': len(documents) / years_back if years_back > 0 else 0
                },
                'analysis_date': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Timeline analysis failed: {e}")
            raise
    
    def _tokenize_vietnamese_text(self, text: str) -> List[str]:
        """Tokenize Vietnamese text"""
        # Basic Vietnamese tokenization
        # Remove punctuation and extra spaces
        text = re.sub(r'[^\w\sàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Split into words
        words = text.strip().split()
        
        # Filter out short words and common stop words
        stop_words = {
            'của', 'và', 'có', 'là', 'để', 'trong', 'với', 'được', 'các', 'này', 'đó',
            'theo', 'về', 'từ', 'tại', 'do', 'bởi', 'trên', 'dưới', 'cho', 'về',
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be'
        }
        
        filtered_words = [
            word for word in words 
            if len(word) > 2 and word.lower() not in stop_words
        ]
        
        return filtered_words
    
    def _extract_legal_terms(self, words: List[str]) -> List[str]:
        """Extract legal-specific terms"""
        legal_keywords = {
            'luật', 'pháp', 'nghị định', 'thông tư', 'quyết định', 'chỉ thị', 'nghị quyết',
            'điều', 'khoản', 'điểm', 'chương', 'mục', 'phần', 'tiểu mục',
            'hình sự', 'dân sự', 'hành chính', 'thương mại', 'lao động',
            'tòa án', 'thẩm phán', 'luật sư', 'kiểm sát', 'công an',
            'vi phạm', 'xử phạt', 'án phạt', 'tù', 'phạt tiền',
            'hợp đồng', 'thỏa thuận', 'cam kết', 'nghĩa vụ', 'quyền lợi',
            'bồi thường', 'thiệt hại', 'tổn thất', 'khiếu nại', 'khiếu kiện',
            'quốc hội', 'chính phủ', 'thủ tướng', 'bộ trưởng', 'ủy ban'
        }
        
        return [word for word in words if word.lower() in legal_keywords]
    
    def _extract_document_references(self, content: str) -> List[str]:
        """Extract document references from content"""
        # Pattern for Vietnamese legal document references
        patterns = [
            r'Luật\s+số\s+(\d+/\d+/[A-Z-]+)',
            r'Nghị định\s+số\s+(\d+/\d+/[A-Z-]+)',
            r'Thông tư\s+số\s+(\d+/\d+/[A-Z-]+)',
            r'Quyết định\s+số\s+(\d+/\d+/[A-Z-]+)',
            r'(\d+/\d+/[A-Z-]+)',
        ]
        
        references = []
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            references.extend(matches)
        
        return list(set(references))  # Remove duplicates
    
    def _find_citation_clusters(self, citation_graph: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Find clusters of documents with similar citation patterns"""
        # Simple clustering based on shared citations
        clusters = []
        processed = set()
        
        for doc1, refs1 in citation_graph.items():
            if doc1 in processed:
                continue
            
            cluster = [doc1]
            processed.add(doc1)
            
            # Find documents with similar citations
            for doc2, refs2 in citation_graph.items():
                if doc2 in processed:
                    continue
                
                # Calculate citation similarity (Jaccard similarity)
                set1 = set(refs1)
                set2 = set(refs2)
                
                if set1 and set2:  # Both have citations
                    similarity = len(set1.intersection(set2)) / len(set1.union(set2))
                    if similarity > 0.3:  # Similarity threshold
                        cluster.append(doc2)
                        processed.add(doc2)
            
            if len(cluster) > 1:  # Only include clusters with multiple documents
                # Find common citations
                all_refs = [citation_graph[doc] for doc in cluster]
                common_refs = set(all_refs[0])
                for refs in all_refs[1:]:
                    common_refs.intersection_update(refs)
                
                clusters.append({
                    'cluster_id': len(clusters),
                    'documents': cluster,
                    'size': len(cluster),
                    'common_citations': list(common_refs),
                    'citation_similarity': sum(
                        len(set(citation_graph[doc1]).intersection(set(citation_graph[doc2]))) 
                        for doc1 in cluster for doc2 in cluster if doc1 != doc2
                    ) / max(len(cluster) * (len(cluster) - 1), 1)
                })
        
        return clusters
    
    def _kmeans_clustering(self, vectors: Dict[str, List[float]], k: int) -> Dict[int, List[str]]:
        """Simple K-means clustering implementation"""
        import random
        
        if len(vectors) < k:
            # If we have fewer documents than clusters, each document is its own cluster
            return {i: [doc_id] for i, doc_id in enumerate(vectors.keys())}
        
        # Initialize centroids randomly
        doc_ids = list(vectors.keys())
        centroids = {}
        
        for i in range(k):
            random_doc = random.choice(doc_ids)
            centroids[i] = vectors[random_doc][:]  # Copy vector
        
        # Iterative clustering
        for iteration in range(10):  # Max 10 iterations
            clusters = {i: [] for i in range(k)}
            
            # Assign documents to closest centroid
            for doc_id, vector in vectors.items():
                closest_cluster = 0
                min_distance = float('inf')
                
                for cluster_id, centroid in centroids.items():
                    # Calculate cosine distance
                    distance = self._cosine_distance(vector, centroid)
                    if distance < min_distance:
                        min_distance = distance
                        closest_cluster = cluster_id
                
                clusters[closest_cluster].append(doc_id)
            
            # Update centroids
            new_centroids = {}
            for cluster_id, doc_list in clusters.items():
                if doc_list:
                    # Calculate mean vector
                    cluster_vectors = [vectors[doc_id] for doc_id in doc_list]
                    mean_vector = [
                        sum(values) / len(values)
                        for values in zip(*cluster_vectors)
                    ]
                    new_centroids[cluster_id] = mean_vector
                else:
                    # Keep old centroid if cluster is empty
                    new_centroids[cluster_id] = centroids[cluster_id]
            
            centroids = new_centroids
        
        return clusters
    
    def _cosine_distance(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine distance between two vectors"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 1.0  # Maximum distance
        
        cosine_similarity = dot_product / (magnitude1 * magnitude2)
        return 1 - cosine_similarity  # Convert to distance
    
    def _calculate_cluster_quality(self, doc_ids: List[str], 
                                 vectors: Dict[str, List[float]], 
                                 all_terms: List[str]) -> float:
        """Calculate cluster quality score"""
        if len(doc_ids) < 2:
            return 0.0
        
        # Calculate intra-cluster similarity
        cluster_vectors = [vectors[doc_id] for doc_id in doc_ids]
        total_similarity = 0.0
        comparisons = 0
        
        for i in range(len(cluster_vectors)):
            for j in range(i + 1, len(cluster_vectors)):
                distance = self._cosine_distance(cluster_vectors[i], cluster_vectors[j])
                similarity = 1 - distance
                total_similarity += similarity
                comparisons += 1
        
        average_similarity = total_similarity / max(comparisons, 1)
        return average_similarity
    
    def _calculate_term_importance(self, terms: List[str], full_text: str) -> Dict[str, float]:
        """Calculate term importance scores"""
        term_counts = Counter(terms)
        total_terms = len(terms)
        
        scores = {}
        for term, count in term_counts.items():
            # TF score
            tf = count / total_terms
            
            # Position score (terms appearing earlier get higher score)
            first_position = full_text.lower().find(term.lower())
            position_score = 1.0 - (first_position / len(full_text)) if first_position != -1 else 0
            
            # Length score (longer terms get higher score)
            length_score = min(len(term) / 10.0, 1.0)
            
            # Combined score
            scores[term] = tf * (1 + position_score * 0.3 + length_score * 0.2)
        
        return scores
    
    def _extract_key_phrases(self, text: str, limit: int) -> List[Tuple[str, float]]:
        """Extract key phrases (2-3 word combinations)"""
        # Simple n-gram extraction
        words = self._tokenize_vietnamese_text(text.lower())
        
        # Extract 2-grams and 3-grams
        phrases = []
        
        # 2-grams
        for i in range(len(words) - 1):
            phrase = f"{words[i]} {words[i+1]}"
            phrases.append(phrase)
        
        # 3-grams
        for i in range(len(words) - 2):
            phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
            phrases.append(phrase)
        
        # Count phrase frequency
        phrase_counts = Counter(phrases)
        
        # Score phrases
        scored_phrases = []
        for phrase, count in phrase_counts.items():
            # Prefer phrases that appear multiple times
            if count >= 2:
                score = count * len(phrase.split())  # Longer phrases get higher score
                scored_phrases.append((phrase, score))
        
        # Sort by score and return top phrases
        scored_phrases.sort(key=lambda x: x[1], reverse=True)
        return scored_phrases[:limit]
    
    def _detect_content_conflicts(self, content1: str, content2: str) -> Dict[str, Any]:
        """Detect conflicts between two document contents"""
        # Simple conflict detection based on contradictory terms
        conflict_patterns = [
            # Prohibition vs Permission
            (['không được', 'cấm', 'bị cấm'], ['được phép', 'cho phép', 'được quyền']),
            # Mandatory vs Optional
            (['phải', 'bắt buộc', 'cần thiết'], ['có thể', 'tự nguyện', 'tùy chọn']),
            # Amount conflicts
            (['tối thiểu', 'ít nhất'], ['tối đa', 'nhiều nhất']),
            # Time conflicts
            (['ngay lập tức', 'tức thì'], ['trong thời hạn', 'chậm nhất']),
        ]
        
        conflicts_found = []
        conflict_score = 0.0
        
        for negative_terms, positive_terms in conflict_patterns:
            # Check if content1 has negative terms and content2 has positive terms
            neg_in_1 = any(term in content1 for term in negative_terms)
            pos_in_2 = any(term in content2 for term in positive_terms)
            
            # Check reverse
            pos_in_1 = any(term in content1 for term in positive_terms)
            neg_in_2 = any(term in content2 for term in negative_terms)
            
            if (neg_in_1 and pos_in_2) or (pos_in_1 and neg_in_2):
                conflicts_found.append({
                    'type': 'contradictory_terms',
                    'content1_terms': [term for term in negative_terms + positive_terms if term in content1],
                    'content2_terms': [term for term in negative_terms + positive_terms if term in content2]
                })
                conflict_score += 0.2
        
        # Check for numerical conflicts
        numbers1 = re.findall(r'\d+', content1)
        numbers2 = re.findall(r'\d+', content2)
        
        if numbers1 and numbers2:
            # Check for significantly different numbers in similar contexts
            for num1 in numbers1[:5]:  # Check first 5 numbers
                for num2 in numbers2[:5]:
                    if abs(int(num1) - int(num2)) > max(int(num1), int(num2)) * 0.5:
                        conflicts_found.append({
                            'type': 'numerical_difference',
                            'value1': num1,
                            'value2': num2,
                            'difference': abs(int(num1) - int(num2))
                        })
                        conflict_score += 0.1
        
        # Determine conflict type
        if conflict_score > 0.7:
            conflict_type = 'high_conflict'
        elif conflict_score > 0.4:
            conflict_type = 'medium_conflict'
        elif conflict_score > 0:
            conflict_type = 'low_conflict'
        else:
            conflict_type = 'no_conflict'
        
        return {
            'conflict_score': min(conflict_score, 1.0),
            'conflict_type': conflict_type,
            'passages': conflicts_found
        }
    
    def _analyze_temporal_conflicts(self, target_doc: Dict[str, Any], 
                                  conflicts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze temporal aspects of conflicts"""
        temporal_conflicts = []
        target_date = target_doc.get('metadata', {}).get('issue_date')
        
        if not target_date:
            return temporal_conflicts
        
        for conflict in conflicts:
            conflict_date = conflict.get('issue_date')
            if conflict_date:
                days_diff = (target_date - conflict_date).days
                
                if days_diff > 0:
                    # Target document is newer
                    temporal_type = 'newer_conflicts_with_older'
                    temporal_significance = 'may_supersede'
                elif days_diff < 0:
                    # Target document is older
                    temporal_type = 'older_conflicts_with_newer'
                    temporal_significance = 'may_be_superseded'
                else:
                    temporal_type = 'same_date'
                    temporal_significance = 'simultaneous_conflict'
                
                temporal_conflicts.append({
                    **conflict,
                    'temporal_type': temporal_type,
                    'temporal_significance': temporal_significance,
                    'days_difference': abs(days_diff)
                })
        
        return sorted(temporal_conflicts, key=lambda x: x['days_difference'])
    
    def _extract_change_keywords(self, content: str) -> List[str]:
        """Extract keywords indicating legal changes"""
        change_keywords = [
            'sửa đổi', 'bổ sung', 'thay thế', 'bãi bỏ', 'hủy bỏ',
            'ban hành', 'công bố', 'có hiệu lực', 'ngừng hiệu lực',
            'điều chỉnh', 'cập nhật', 'hoàn thiện', 'tăng cường'
        ]
        
        found_keywords = []
        content_lower = content.lower()
        
        for keyword in change_keywords:
            if keyword in content_lower:
                found_keywords.append(keyword)
        
        return found_keywords
    
    def _classify_amendment(self, content: str) -> str:
        """Classify type of amendment"""
        content_lower = content.lower()
        
        if any(term in content_lower for term in ['bãi bỏ', 'hủy bỏ', 'ngừng hiệu lực']):
            return 'repeal'
        elif any(term in content_lower for term in ['sửa đổi', 'điều chỉnh']):
            return 'amendment'
        elif any(term in content_lower for term in ['bổ sung', 'thêm']):
            return 'addition'
        elif any(term in content_lower for term in ['thay thế']):
            return 'replacement'
        else:
            return 'other'