"""
Crawling Service
Service for crawling legal documents from official sources
"""

import asyncio
import aiohttp
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

class CrawlingService:
    """Service for crawling legal documents"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Official Vietnam legal document sources
        self.sources = {
            "vanban.chinhphu.vn": {
                "base_url": "https://vanban.chinhphu.vn",
                "search_endpoint": "/portal/page/portal/chinhphu/trangchu/vanban",
                "parser": self._parse_chinhphu_vn
            },
            "thuvienphapluat.vn": {
                "base_url": "https://thuvienphapluat.vn",
                "search_endpoint": "/van-ban-phap-luat",
                "parser": self._parse_thuvienphapluat_vn
            },
            "congbao.chinhphu.vn": {
                "base_url": "https://congbao.chinhphu.vn",
                "search_endpoint": "/cb/public/tim-kiem-cong-bao",
                "parser": self._parse_congbao_chinhphu_vn
            }
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def crawl_documents_by_category(self, category: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Crawl documents by legal category"""
        documents = []
        
        for source_name, source_config in self.sources.items():
            try:
                source_docs = await self._crawl_from_source(
                    source_name, source_config, category, limit // len(self.sources)
                )
                documents.extend(source_docs)
            except Exception as e:
                logger.error(f"Failed to crawl from {source_name}: {e}")
                continue
        
        return documents
    
    async def crawl_documents_by_date_range(self, start_date: datetime, end_date: datetime, limit: int = 100) -> List[Dict[str, Any]]:
        """Crawl documents within a date range"""
        documents = []
        
        for source_name, source_config in self.sources.items():
            try:
                source_docs = await self._crawl_from_source_by_date(
                    source_name, source_config, start_date, end_date, limit // len(self.sources)
                )
                documents.extend(source_docs)
            except Exception as e:
                logger.error(f"Failed to crawl from {source_name}: {e}")
                continue
        
        return documents
    
    async def _crawl_from_source(self, source_name: str, source_config: Dict[str, Any], 
                                category: str, limit: int) -> List[Dict[str, Any]]:
        """Crawl documents from a specific source"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        documents = []
        search_url = f"{source_config['base_url']}{source_config['search_endpoint']}"
        
        # Build search parameters based on category
        params = self._build_search_params(source_name, category, limit)
        
        async with self.session.get(search_url, params=params) as response:
            if response.status == 200:
                html = await response.text()
                documents = await source_config['parser'](html, source_config['base_url'])
            else:
                logger.warning(f"Failed to fetch from {source_name}: {response.status}")
        
        return documents[:limit]
    
    async def _crawl_from_source_by_date(self, source_name: str, source_config: Dict[str, Any], 
                                       start_date: datetime, end_date: datetime, limit: int) -> List[Dict[str, Any]]:
        """Crawl documents from a source within date range"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        documents = []
        search_url = f"{source_config['base_url']}{source_config['search_endpoint']}"
        
        # Build search parameters based on date range
        params = self._build_date_search_params(source_name, start_date, end_date, limit)
        
        async with self.session.get(search_url, params=params) as response:
            if response.status == 200:
                html = await response.text()
                documents = await source_config['parser'](html, source_config['base_url'])
            else:
                logger.warning(f"Failed to fetch from {source_name}: {response.status}")
        
        return documents[:limit]
    
    def _build_search_params(self, source_name: str, category: str, limit: int) -> Dict[str, str]:
        """Build search parameters for specific source"""
        if source_name == "vanban.chinhphu.vn":
            return {
                "keyword": category,
                "pageSize": str(limit),
                "page": "1"
            }
        elif source_name == "thuvienphapluat.vn":
            return {
                "keyword": category,
                "page": "1",
                "pagesize": str(limit)
            }
        elif source_name == "congbao.chinhphu.vn":
            return {
                "keyword": category,
                "page": "1",
                "size": str(limit)
            }
        return {}
    
    def _build_date_search_params(self, source_name: str, start_date: datetime, 
                                end_date: datetime, limit: int) -> Dict[str, str]:
        """Build date-based search parameters"""
        start_str = start_date.strftime("%d/%m/%Y")
        end_str = end_date.strftime("%d/%m/%Y")
        
        if source_name == "vanban.chinhphu.vn":
            return {
                "fromDate": start_str,
                "toDate": end_str,
                "pageSize": str(limit),
                "page": "1"
            }
        elif source_name == "thuvienphapluat.vn":
            return {
                "fromdate": start_str,
                "todate": end_str,
                "page": "1",
                "pagesize": str(limit)
            }
        elif source_name == "congbao.chinhphu.vn":
            return {
                "fromDate": start_str,
                "toDate": end_str,
                "page": "1",
                "size": str(limit)
            }
        return {}
    
    async def _parse_chinhphu_vn(self, html: str, base_url: str) -> List[Dict[str, Any]]:
        """Parse documents from chinhphu.vn"""
        documents = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find document items (this is a sample structure, actual structure may vary)
        doc_items = soup.find_all('div', class_='document-item')
        
        for item in doc_items:
            try:
                title_elem = item.find('a', class_='doc-title')
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                url = urljoin(base_url, title_elem.get('href', ''))
                
                # Extract metadata
                metadata = {}
                
                # Document number
                doc_num_elem = item.find('span', class_='doc-number')
                if doc_num_elem:
                    metadata['document_number'] = doc_num_elem.get_text(strip=True)
                
                # Issue date
                date_elem = item.find('span', class_='issue-date')
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    metadata['issue_date'] = self._parse_vietnamese_date(date_text)
                
                # Issuing agency
                agency_elem = item.find('span', class_='issuing-agency')
                if agency_elem:
                    metadata['issuing_agency'] = agency_elem.get_text(strip=True)
                
                # Document type
                type_elem = item.find('span', class_='doc-type')
                if type_elem:
                    metadata['document_type'] = type_elem.get_text(strip=True)
                
                # Get full content
                content = await self._fetch_document_content(url)
                
                documents.append({
                    'title': title,
                    'content': content,
                    'source_url': url,
                    'source': 'vanban.chinhphu.vn',
                    'metadata': metadata,
                    'crawled_at': datetime.utcnow()
                })
                
            except Exception as e:
                logger.error(f"Error parsing document from chinhphu.vn: {e}")
                continue
        
        return documents
    
    async def _parse_thuvienphapluat_vn(self, html: str, base_url: str) -> List[Dict[str, Any]]:
        """Parse documents from thuvienphapluat.vn"""
        documents = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find document items
        doc_items = soup.find_all('div', class_='document-result-item')
        
        for item in doc_items:
            try:
                title_elem = item.find('h3', class_='title')
                if not title_elem or not title_elem.find('a'):
                    continue
                
                title_link = title_elem.find('a')
                title = title_link.get_text(strip=True)
                url = urljoin(base_url, title_link.get('href', ''))
                
                # Extract metadata
                metadata = {}
                
                # Document details
                details = item.find('div', class_='document-details')
                if details:
                    detail_items = details.find_all('span')
                    for detail in detail_items:
                        text = detail.get_text(strip=True)
                        if 'Số hiệu:' in text:
                            metadata['document_number'] = text.replace('Số hiệu:', '').strip()
                        elif 'Ngày ban hành:' in text:
                            date_text = text.replace('Ngày ban hành:', '').strip()
                            metadata['issue_date'] = self._parse_vietnamese_date(date_text)
                        elif 'Cơ quan ban hành:' in text:
                            metadata['issuing_agency'] = text.replace('Cơ quan ban hành:', '').strip()
                        elif 'Loại văn bản:' in text:
                            metadata['document_type'] = text.replace('Loại văn bản:', '').strip()
                
                # Get full content
                content = await self._fetch_document_content(url)
                
                documents.append({
                    'title': title,
                    'content': content,
                    'source_url': url,
                    'source': 'thuvienphapluat.vn',
                    'metadata': metadata,
                    'crawled_at': datetime.utcnow()
                })
                
            except Exception as e:
                logger.error(f"Error parsing document from thuvienphapluat.vn: {e}")
                continue
        
        return documents
    
    async def _parse_congbao_chinhphu_vn(self, html: str, base_url: str) -> List[Dict[str, Any]]:
        """Parse documents from congbao.chinhphu.vn"""
        documents = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find document items
        doc_items = soup.find_all('div', class_='cb-item')
        
        for item in doc_items:
            try:
                title_elem = item.find('h4', class_='cb-title')
                if not title_elem or not title_elem.find('a'):
                    continue
                
                title_link = title_elem.find('a')
                title = title_link.get_text(strip=True)
                url = urljoin(base_url, title_link.get('href', ''))
                
                # Extract metadata
                metadata = {}
                
                # Document info
                info_elem = item.find('div', class_='cb-info')
                if info_elem:
                    info_text = info_elem.get_text(strip=True)
                    
                    # Extract document number
                    doc_num_match = re.search(r'Số (\d+/\d+)', info_text)
                    if doc_num_match:
                        metadata['document_number'] = doc_num_match.group(1)
                    
                    # Extract date
                    date_match = re.search(r'ngày (\d{1,2}/\d{1,2}/\d{4})', info_text)
                    if date_match:
                        metadata['issue_date'] = self._parse_vietnamese_date(date_match.group(1))
                
                # Get full content
                content = await self._fetch_document_content(url)
                
                documents.append({
                    'title': title,
                    'content': content,
                    'source_url': url,
                    'source': 'congbao.chinhphu.vn',
                    'metadata': metadata,
                    'crawled_at': datetime.utcnow()
                })
                
            except Exception as e:
                logger.error(f"Error parsing document from congbao.chinhphu.vn: {e}")
                continue
        
        return documents
    
    async def _fetch_document_content(self, url: str) -> str:
        """Fetch full content of a document"""
        if not self.session:
            return ""
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Remove script, style, and other non-content elements
                    for element in soup(['script', 'style', 'nav', 'header', 'footer']):
                        element.decompose()
                    
                    # Extract main content (common selectors)
                    content_selectors = [
                        '.document-content',
                        '.content',
                        '.main-content',
                        '.article-content',
                        '#content',
                        '.post-content'
                    ]
                    
                    for selector in content_selectors:
                        content_elem = soup.select_one(selector)
                        if content_elem:
                            return content_elem.get_text(strip=True, separator='\n')
                    
                    # Fallback: get all text from body
                    body = soup.find('body')
                    if body:
                        return body.get_text(strip=True, separator='\n')
                    
                    return soup.get_text(strip=True, separator='\n')
        except Exception as e:
            logger.error(f"Failed to fetch content from {url}: {e}")
            return ""
        
        return ""
    
    def _parse_vietnamese_date(self, date_text: str) -> Optional[datetime]:
        """Parse Vietnamese date string to datetime"""
        if not date_text:
            return None
        
        # Common Vietnamese date formats
        date_patterns = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # dd/mm/yyyy
            r'(\d{1,2})-(\d{1,2})-(\d{4})',  # dd-mm-yyyy
            r'ngày (\d{1,2}) tháng (\d{1,2}) năm (\d{4})',  # Vietnamese format
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_text)
            if match:
                try:
                    if 'ngày' in pattern:  # Vietnamese format
                        day, month, year = match.groups()
                    else:  # Standard format
                        day, month, year = match.groups()
                    
                    return datetime(int(year), int(month), int(day))
                except ValueError:
                    continue
        
        return None
    
    async def save_crawled_documents(self, documents: List[Dict[str, Any]]) -> int:
        """Save crawled documents to database"""
        if not documents:
            return 0
        
        saved_count = 0
        
        for doc_data in documents:
            try:
                # Check for duplicates by title and source
                existing = await self.db.documents.find_one({
                    'title': doc_data['title'],
                    'source': doc_data['source']
                })
                
                if existing:
                    logger.info(f"Document already exists: {doc_data['title']}")
                    continue
                
                # Create document
                document = {
                    'title': doc_data['title'],
                    'content': doc_data['content'],
                    'category': self._classify_document(doc_data['title'], doc_data['content']),
                    'tags': self._extract_tags(doc_data['title'], doc_data['content']),
                    'source_url': doc_data.get('source_url'),
                    'source': doc_data.get('source'),
                    'metadata': doc_data.get('metadata', {}),
                    'date_created': datetime.utcnow(),
                    'crawled_at': doc_data.get('crawled_at', datetime.utcnow())
                }
                
                # Add issue date if available
                if 'issue_date' in doc_data.get('metadata', {}):
                    document['issue_date'] = doc_data['metadata']['issue_date']
                
                await self.db.documents.insert_one(document)
                saved_count += 1
                
            except Exception as e:
                logger.error(f"Failed to save document: {e}")
                continue
        
        logger.info(f"Saved {saved_count} documents from crawling")
        return saved_count
    
    def _classify_document(self, title: str, content: str) -> str:
        """Classify document based on title and content"""
        text = f"{title} {content}".lower()
        
        # Legal categories mapping
        categories = {
            'hiến pháp': ['hiến pháp', 'constitution'],
            'luật': ['luật', 'law', 'bộ luật'],
            'nghị định': ['nghị định', 'decree'],
            'thông tư': ['thông tư', 'circular'],
            'quyết định': ['quyết định', 'decision'],
            'chỉ thị': ['chỉ thị', 'directive'],
            'nghị quyết': ['nghị quyết', 'resolution'],
            'hướng dẫn': ['hướng dẫn', 'guideline'],
            'dân sự': ['dân sự', 'civil'],
            'hình sự': ['hình sự', 'criminal', 'tội phạm'],
            'hành chính': ['hành chính', 'administrative'],
            'lao động': ['lao động', 'labor', 'employment'],
            'thương mại': ['thương mại', 'commerce', 'kinh doanh'],
            'đầu tư': ['đầu tư', 'investment'],
            'thuế': ['thuế', 'tax'],
            'đất đai': ['đất đai', 'land', 'bất động sản'],
            'môi trường': ['môi trường', 'environment'],
            'giáo dục': ['giáo dục', 'education'],
            'y tế': ['y tế', 'health', 'sức khỏe'],
        }
        
        for category, keywords in categories.items():
            if any(keyword in text for keyword in keywords):
                return category
        
        return 'khác'  # Other
    
    def _extract_tags(self, title: str, content: str) -> List[str]:
        """Extract tags from document title and content"""
        text = f"{title} {content}".lower()
        tags = []
        
        # Common legal terms as tags
        legal_terms = [
            'luật', 'nghị định', 'thông tư', 'quyết định', 'chỉ thị', 'nghị quyết',
            'dân sự', 'hình sự', 'hành chính', 'lao động', 'thương mại',
            'đầu tư', 'thuế', 'đất đai', 'môi trường', 'giáo dục', 'y tế',
            'chính phủ', 'bộ', 'ủy ban', 'quốc hội', 'thủ tướng'
        ]
        
        for term in legal_terms:
            if term in text:
                tags.append(term)
        
        # Extract year if present
        year_match = re.search(r'\b(20\d{2})\b', text)
        if year_match:
            tags.append(f"năm_{year_match.group(1)}")
        
        return list(set(tags))  # Remove duplicates