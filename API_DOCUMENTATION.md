# Hệ thống Quản lý Văn bản Pháp luật - API Documentation

## Tổng quan hệ thống
Hệ thống quản lý văn bản pháp luật hoàn chỉnh với 6 module chính:

1. **Crawling & Storage** - Thu thập văn bản từ các nguồn chính phủ
2. **Text Processing & Standardization** - Xử lý văn bản nâng cao với OCR
3. **Full-Text Search & Mining** - Tìm kiếm và khai thác dữ liệu
4. **Text Analysis** - Phân tích văn bản và phát hiện xung đột
5. **Advanced Querying** - Truy vấn phức tạp
6. **Reports & Dashboard** - Báo cáo và dashboard

## API Endpoints

### 1. Crawling Module (`/api/crawling`)

#### GET `/api/crawling/sources`
**Mô tả:** Lấy danh sách các nguồn crawling được hỗ trợ
```json
{
    "sources": [
        {
            "name": "vanban.chinhphu.vn",
            "description": "Văn bản Chính phủ",
            "url": "https://vanban.chinhphu.vn"
        },
        {
            "name": "thuvienphapluat.vn", 
            "description": "Thư viện Pháp luật",
            "url": "https://thuvienphapluat.vn"
        },
        {
            "name": "congbao.chinhphu.vn",
            "description": "Công báo Chính phủ",
            "url": "https://congbao.chinhphu.vn"
        }
    ]
}
```

#### POST `/api/crawling/crawl`
**Mô tả:** Bắt đầu crawl văn bản từ nguồn được chỉ định
**Body:**
```json
{
    "source": "vanban.chinhphu.vn",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "document_types": ["quyet_dinh", "thong_tu"],
    "max_documents": 100
}
```

#### GET `/api/crawling/status/{task_id}`
**Mô tả:** Kiểm tra trạng thái crawling task

#### POST `/api/crawling/stop/{task_id}`
**Mô tả:** Dừng crawling task

#### GET `/api/crawling/history`
**Mô tả:** Lấy lịch sử crawling với phân trang

### 2. Enhanced Processing Module (`/api/processing`)

#### POST `/api/processing/upload`
**Mô tả:** Upload và xử lý văn bản (hỗ trợ OCR)
**Form Data:**
- `file`: File văn bản (PDF, DOCX, TXT, RTF, ODT, images)
- `enable_ocr`: boolean (optional)
- `extract_metadata`: boolean (optional)
- `detect_structure`: boolean (optional)

#### POST `/api/processing/process-text`
**Mô tả:** Xử lý văn bản từ text input
**Body:**
```json
{
    "text": "Nội dung văn bản...",
    "title": "Tiêu đề văn bản",
    "extract_entities": true,
    "detect_structure": true,
    "extract_citations": true
}
```

#### GET `/api/processing/document/{document_id}/versions`
**Mô tả:** Lấy lịch sử phiên bản văn bản

#### POST `/api/processing/document/{document_id}/update`
**Mô tả:** Cập nhật văn bản và tạo phiên bản mới

#### GET `/api/processing/duplicates`
**Mô tả:** Phát hiện văn bản trùng lặp

#### POST `/api/processing/merge-duplicates`
**Mô tả:** Gộp các văn bản trùng lặp

### 3. Advanced Search Module (`/api/search`)

#### POST `/api/search/text`
**Mô tả:** Tìm kiếm văn bản (6 loại tìm kiếm)
**Body:**
```json
{
    "query": "từ khóa tìm kiếm",
    "search_type": "full_text", // full_text, boolean, phrase, proximity, wildcard, fuzzy
    "filters": {
        "document_type": ["quyet_dinh"],
        "date_range": {
            "start": "2024-01-01",
            "end": "2024-12-31"
        },
        "issuing_agency": ["chinh_phu"]
    },
    "sort": {
        "field": "relevance",
        "order": "desc"
    },
    "limit": 20,
    "offset": 0
}
```

#### GET `/api/search/suggestions`
**Mô tả:** Gợi ý tìm kiếm thông minh

#### POST `/api/search/faceted`
**Mô tả:** Tìm kiếm với facets

#### POST `/api/search/saved`
**Mô tả:** Lưu truy vấn tìm kiếm

#### GET `/api/search/saved`
**Mô tả:** Lấy danh sách truy vấn đã lưu

#### GET `/api/search/analytics/{search_id}`
**Mô tả:** Phân tích hiệu suất tìm kiếm

### 4. Text Analysis Module (`/api/analysis`)

#### POST `/api/analysis/cluster`
**Mô tả:** Phân cụm văn bản
**Body:**
```json
{
    "document_ids": ["id1", "id2", "id3"],
    "method": "kmeans", // kmeans, hierarchical
    "num_clusters": 5,
    "features": ["tfidf", "semantic"]
}
```

#### POST `/api/analysis/compare`
**Mô tả:** So sánh văn bản
**Body:**
```json
{
    "document_id1": "id1",
    "document_id2": "id2",
    "comparison_type": "similarity" // similarity, difference, conflict
}
```

#### POST `/api/analysis/extract-keywords`
**Mô tả:** Trích xuất từ khóa
**Body:**
```json
{
    "document_ids": ["id1", "id2"],
    "method": "tfidf", // tfidf, textrank
    "max_keywords": 10
}
```

#### POST `/api/analysis/detect-conflicts`
**Mô tả:** Phát hiện xung đột pháp lý
**Body:**
```json
{
    "document_ids": ["id1", "id2"],
    "conflict_types": ["contradiction", "overlap", "inconsistency"]
}
```

#### POST `/api/analysis/citation-network`
**Mô tả:** Phân tích mạng trích dẫn
**Body:**
```json
{
    "document_ids": ["id1", "id2", "id3"],
    "include_external": true,
    "max_depth": 3
}
```

#### POST `/api/analysis/summarize`
**Mô tả:** Tóm tắt văn bản
**Body:**
```json
{
    "document_ids": ["id1"],
    "summary_type": "extractive", // extractive, abstractive
    "max_sentences": 5
}
```

### 5. Advanced Querying Module (`/api/query`)

#### POST `/api/query/build`
**Mô tả:** Xây dựng truy vấn phức tạp
**Body:**
```json
{
    "query_type": "complex",
    "conditions": [
        {
            "field": "document_type",
            "operator": "equals",
            "value": "quyet_dinh"
        },
        {
            "field": "content",
            "operator": "contains",
            "value": "thuế"
        }
    ],
    "logic": "AND",
    "aggregations": ["count", "group_by_agency"],
    "include_analytics": true
}
```

#### POST `/api/query/execute`
**Mô tả:** Thực thi truy vấn đã xây dựng

#### GET `/api/query/templates`
**Mô tả:** Lấy template truy vấn có sẵn

#### POST `/api/query/save-template`
**Mô tả:** Lưu template truy vấn mới

### 6. Reports & Dashboard Module (`/api/reports`)

#### GET `/api/reports/search-analytics`
**Mô tả:** Báo cáo phân tích tìm kiếm
**Query Parameters:**
- `start_date`: Ngày bắt đầu
- `end_date`: Ngày kết thúc
- `group_by`: Nhóm theo (daily, weekly, monthly)

#### GET `/api/reports/document-statistics`
**Mô tả:** Thống kê văn bản

#### GET `/api/reports/compliance-tracking`
**Mô tả:** Theo dõi tuân thủ pháp lý

#### GET `/api/reports/usage-metrics`
**Mô tả:** Số liệu sử dụng hệ thống

#### GET `/api/reports/performance-monitoring`
**Mô tả:** Giám sát hiệu suất

#### GET `/api/reports/export/{report_type}`
**Mô tả:** Xuất báo cáo (Excel, PDF, CSV)
**Query Parameters:**
- `format`: excel, pdf, csv
- `start_date`, `end_date`: Khoảng thời gian

## Document Model Structure

```json
{
    "_id": "ObjectId",
    "title": "string",
    "content": "string",
    "document_type": "string",
    "document_number": "string", 
    "issuing_agency": "string",
    "issue_date": "datetime",
    "effective_date": "datetime",
    "expiry_date": "datetime",
    "status": "string",
    "classification": "string",
    "tags": ["string"],
    "metadata": {
        "file_type": "string",
        "file_size": "number",
        "page_count": "number",
        "language": "string",
        "encoding": "string",
        "ocr_confidence": "number"
    },
    "processing_info": {
        "extracted_entities": ["string"],
        "detected_structure": "object",
        "citations": ["string"],
        "summary": "string"
    },
    "version_info": {
        "version": "number",
        "created_at": "datetime",
        "updated_at": "datetime",
        "parent_version": "ObjectId"
    },
    "search_metadata": {
        "indexed_at": "datetime",
        "search_count": "number",
        "last_accessed": "datetime"
    }
}
```

## Error Handling

Tất cả endpoints sử dụng HTTP status codes chuẩn:
- `200`: Success
- `201`: Created  
- `400`: Bad Request
- `401`: Unauthorized
- `404`: Not Found
- `422`: Validation Error
- `500`: Internal Server Error

Error response format:
```json
{
    "error": "error_code",
    "message": "Mô tả lỗi",
    "details": "object (optional)"
}
```

## Authentication

Hệ thống sử dụng JWT tokens cho authentication:
```
Authorization: Bearer <jwt_token>
```

## Rate Limiting

- Crawling API: 10 requests/minute
- Search API: 100 requests/minute  
- Other APIs: 60 requests/minute

## Setup và Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure MongoDB connection in `.env`:
```
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/
DATABASE_NAME=legal_documents
```

3. Run the application:
```bash
python main.py
```

4. Access API documentation: `http://localhost:8000/docs`

## Vietnamese Language Support

Hệ thống được tối ưu hóa cho tiếng Việt:
- Tokenization cho tiếng Việt
- OCR hỗ trợ tiếng Việt
- Từ điển thuật ngữ pháp lý Việt Nam
- Phân tích cấu trúc văn bản pháp lý Việt Nam
- Crawling từ các trang web chính phủ Việt Nam