# Hướng dẫn Deployment - Hệ thống Quản lý Văn bản Pháp luật

## Tổng quan
Hệ thống được thiết kế để chạy trên Docker với các services:
- Backend: FastAPI application
- Frontend: React TypeScript application  
- Database: MongoDB Atlas (cloud)

## Prerequisites

### 1. System Requirements
- Docker & Docker Compose
- MongoDB Atlas account
- Python 3.9+ (cho development)
- Node.js 18+ (cho frontend development)

### 2. External Services
- **MongoDB Atlas**: Database chính
- **Google AI Services**: Cho AI/LLM features (optional)

## Environment Configuration

### Backend Environment (`.env`)
```bash
# Database
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/
DATABASE_NAME=legal_documents

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI Services (Optional)
GOOGLE_AI_API_KEY=your-google-ai-key

# Application Settings
DEBUG=false
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# Crawling Settings
CRAWLING_DELAY=2
MAX_CONCURRENT_CRAWLS=5
USER_AGENT=LegalDocCrawler/1.0

# OCR Settings (Optional)
TESSERACT_PATH=/usr/bin/tesseract
TESSERACT_LANG=vie
```

### Frontend Environment (`.env.local`)
```bash
REACT_APP_API_URL=http://localhost:8000
REACT_APP_API_VERSION=v1
REACT_APP_ENVIRONMENT=development
```

## MongoDB Atlas Setup

### 1. Create Atlas Cluster
1. Đăng ký tài khoản MongoDB Atlas
2. Tạo cluster (M0 tier cho development)
3. Tạo database user với quyền readWrite
4. Whitelist IP addresses

### 2. Create Database Collections
```javascript
// Chạy script này trong MongoDB Atlas console
use legal_documents

// Tạo collections với indexes
db.createCollection("documents")
db.documents.createIndex({ "title": "text", "content": "text" })
db.documents.createIndex({ "document_type": 1 })
db.documents.createIndex({ "issuing_agency": 1 })
db.documents.createIndex({ "issue_date": -1 })
db.documents.createIndex({ "tags": 1 })

db.createCollection("crawling_tasks")
db.crawling_tasks.createIndex({ "created_at": -1 })
db.crawling_tasks.createIndex({ "status": 1 })

db.createCollection("search_analytics")
db.search_analytics.createIndex({ "timestamp": -1 })
db.search_analytics.createIndex({ "query": 1 })

db.createCollection("user_sessions")
db.user_sessions.createIndex({ "user_id": 1 })
db.user_sessions.createIndex({ "created_at": 1 }, { expireAfterSeconds: 86400 })
```

## Docker Deployment

### 1. Build Images
```bash
# Build backend
cd backend
docker build -t legal-doc-backend .

# Build frontend  
cd ../frontend
docker build -t legal-doc-frontend .
```

### 2. Docker Compose Production
Tạo file `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - MONGODB_URL=${MONGODB_URL}
      - DATABASE_NAME=${DATABASE_NAME}
      - SECRET_KEY=${SECRET_KEY}
      - DEBUG=false
      - LOG_LEVEL=INFO
    volumes:
      - ./logs:/app/logs
      - ./uploads:/app/uploads
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=${BACKEND_URL}
    depends_on:
      - backend
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - frontend
      - backend
    restart: unless-stopped

volumes:
  logs:
  uploads:
```

### 3. Start Services
```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f backend
```

## Nginx Configuration

Tạo file `nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }
    
    upstream frontend {
        server frontend:3000;
    }

    server {
        listen 80;
        server_name yourdomain.com;
        
        # Redirect HTTP to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com;
        
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        
        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # Backend API
        location /api {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Increase timeout for long crawling operations
            proxy_read_timeout 300s;
            proxy_connect_timeout 75s;
        }
        
        # File uploads
        location /api/processing/upload {
            proxy_pass http://backend;
            client_max_body_size 50M;
            proxy_request_buffering off;
        }
    }
}
```

## Monitoring & Logging

### 1. Application Logs
```bash
# Backend logs
docker-compose logs -f backend

# Nginx logs
docker-compose logs -f nginx

# All services
docker-compose logs -f
```

### 2. Health Checks
Backend health endpoint: `GET /health`
```json
{
    "status": "healthy",
    "timestamp": "2024-01-01T00:00:00Z",
    "version": "1.0.0",
    "database": "connected",
    "services": {
        "crawling": "active",
        "search": "active",
        "analysis": "active"
    }
}
```

### 3. Monitoring Setup
```bash
# Install monitoring stack (optional)
docker run -d \
  --name=prometheus \
  -p 9090:9090 \
  prom/prometheus

docker run -d \
  --name=grafana \
  -p 3001:3000 \
  grafana/grafana
```

## Performance Optimization

### 1. Database Optimization
```javascript
// Tạo compound indexes
db.documents.createIndex({ 
    "document_type": 1, 
    "issue_date": -1 
})

db.documents.createIndex({ 
    "issuing_agency": 1, 
    "status": 1,
    "issue_date": -1 
})

// Text search optimization
db.documents.createIndex({
    "title": "text",
    "content": "text",
    "tags": "text"
}, {
    weights: {
        "title": 10,
        "content": 5,
        "tags": 3
    },
    name: "document_text_search"
})
```

### 2. Application Optimization
```bash
# Backend optimizations in production
export WORKERS=4
export MAX_REQUESTS=1000
export MAX_REQUESTS_JITTER=50
export PRELOAD=true

uvicorn main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers $WORKERS \
  --max-requests $MAX_REQUESTS \
  --max-requests-jitter $MAX_REQUESTS_JITTER \
  --preload
```

### 3. Caching Strategy
```python
# Redis cache setup (optional)
# Add to docker-compose.yml
redis:
  image: redis:alpine
  ports:
    - "6379:6379"
  restart: unless-stopped
```

## Backup & Recovery

### 1. Database Backup
```bash
# MongoDB Atlas automatic backups
# Hoặc manual backup:
mongodump --uri="mongodb+srv://user:pass@cluster.mongodb.net/legal_documents" --out=./backup/$(date +%Y%m%d)
```

### 2. File Backup
```bash
# Backup uploaded files
docker run --rm -v legal-doc_uploads:/data -v $(pwd):/backup alpine tar czf /backup/uploads-$(date +%Y%m%d).tar.gz -C /data .

# Backup logs
docker run --rm -v legal-doc_logs:/data -v $(pwd):/backup alpine tar czf /backup/logs-$(date +%Y%m%d).tar.gz -C /data .
```

## Troubleshooting

### 1. Common Issues

**Backend không start:**
```bash
# Check logs
docker-compose logs backend

# Check environment variables
docker-compose exec backend printenv

# Test database connection
docker-compose exec backend python -c "
from app.database import get_database
import asyncio
async def test():
    db = await get_database()
    print('DB connected:', db.name)
asyncio.run(test())
"
```

**OCR không hoạt động:**
```bash
# Install tesseract trong container
docker-compose exec backend apt-get update && apt-get install -y tesseract-ocr tesseract-ocr-vie

# Test OCR
docker-compose exec backend tesseract --version
```

**Crawling lỗi:**
```bash
# Check network connectivity
docker-compose exec backend ping vanban.chinhphu.vn

# Check user agent blocking
docker-compose exec backend curl -I -A "Mozilla/5.0" https://vanban.chinhphu.vn
```

### 2. Performance Issues

**Slow search:**
```javascript
// Check indexes
db.documents.getIndexes()

// Analyze query performance
db.documents.find({"$text": {"$search": "query"}}).explain("executionStats")
```

**High memory usage:**
```bash
# Monitor container resources
docker stats

# Adjust memory limits in docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

## Security Considerations

### 1. Environment Security
- Sử dụng Docker secrets cho sensitive data
- Rotate database passwords định kỳ
- Enable MongoDB Atlas IP whitelist
- Use HTTPS với valid certificates

### 2. Application Security
- Rate limiting cho crawling endpoints
- Input validation và sanitization
- File upload size limits
- CORS configuration properly

### 3. Network Security
```yaml
# Docker network isolation
networks:
  internal:
    driver: bridge
    internal: true
  external:
    driver: bridge

services:
  backend:
    networks:
      - internal
      - external
```

## Scaling Considerations

### 1. Horizontal Scaling
```yaml
# Scale backend instances
docker-compose up -d --scale backend=3

# Load balancer configuration
nginx:
  # Update upstream to include multiple backends
  upstream backend {
    server backend_1:8000;
    server backend_2:8000; 
    server backend_3:8000;
  }
```

### 2. Database Scaling
- MongoDB Atlas cluster tier upgrade
- Read replicas cho read-heavy workloads
- Sharding cho large datasets

Hệ thống hiện tại đã sẵn sàng để deployment và sử dụng trong môi trường production!