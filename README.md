# Hệ thống Tra cứu Văn bản Pháp luật với AI

Hệ thống số hóa và tra cứu văn bản pháp luật với AI, giúp tìm kiếm thông minh và hỏi đáp tự nhiên về các quy định pháp lý.

## 🏗️ Kiến trúc hệ thống

### Backend
- **FastAPI**: RESTful API với async support
- **MongoDB**: Lưu trữ văn bản + full-text search + vector search  
- **AI Integration**: Sentence-BERT cho semantic search, LLM cho Q&A

### Frontend
- **React 18**: Component-based UI
- **Material-UI**: Component library
- **React Query**: API state management

## 🚀 Tính năng chính

### 1. Tìm kiếm thông minh
- **Tìm kiếm văn bản**: Tìm kiếm dựa trên từ khóa chính xác
- **Tìm kiếm ngữ nghĩa**: Sử dụng AI để hiểu ý nghĩa và tìm tài liệu liên quan

### 2. Số hóa tài liệu
- Hỗ trợ upload file PDF, DOC, DOCX, TXT
- Tự động trích xuất và xử lý nội dung
- Tạo vector embedding cho tìm kiếm ngữ nghĩa

### 3. Hỏi đáp AI
- Đặt câu hỏi bằng ngôn ngữ tự nhiên
- AI trả lời dựa trên cơ sở dữ liệu pháp luật
- Hiển thị độ tin cậy và nguồn tài liệu tham khảo

### 4. Quản lý tài liệu
- Xem, chỉnh sửa, xóa tài liệu
- Phân loại theo danh mục
- Gắn thẻ và metadata

## 🛠️ Cài đặt và chạy

### Yêu cầu hệ thống
- Python 3.11+
- Node.js 18+
- MongoDB 7.0+
- Docker & Docker Compose (tùy chọn)

### Cách 1: Chạy với Docker (Khuyến nghị)

```bash
# Clone repository
git clone https://github.com/thanthienhai/ths-csdl-nang-cao.git
cd ths-csdl-nang-cao

# Tạo file environment (tùy chọn: thêm OpenAI API key)
echo "OPENAI_API_KEY=your-openai-api-key-here" > .env

# Chạy tất cả services
docker-compose up -d

# Xem logs
docker-compose logs -f
```

Truy cập:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Cách 2: Chạy thủ công

#### Backend

```bash
cd backend

# Tạo virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc venv\Scripts\activate  # Windows

# Cài đặt dependencies
pip install -r requirements.txt

# Copy và chỉnh sửa file environment
cp .env.example .env
# Chỉnh sửa .env với thông tin MongoDB và OpenAI API key

# Chạy server
uvicorn main:app --reload
```

#### Frontend

```bash
cd frontend

# Cài đặt dependencies
npm install

# Chạy development server
npm start
```

#### MongoDB

```bash
# Chạy MongoDB với Docker
docker run -d \
  --name mongodb \
  -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=password123 \
  mongo:7.0
```

## 📖 Hướng dẫn sử dụng

### 1. Tải lên tài liệu
1. Vào trang "Tải lên"
2. Chọn file (PDF, DOC, DOCX, TXT)
3. Nhập tiêu đề và chọn danh mục
4. Thêm từ khóa (tùy chọn)
5. Click "Tải lên"

### 2. Tìm kiếm tài liệu
1. Vào trang "Tìm kiếm"
2. Nhập từ khóa tìm kiếm
3. Chọn loại tìm kiếm:
   - **Văn bản**: Tìm theo từ khóa chính xác
   - **Ngữ nghĩa AI**: Tìm theo ý nghĩa
4. Lọc theo danh mục (tùy chọn)

### 3. Hỏi đáp AI
1. Vào trang "Hỏi đáp AI"
2. Đặt câu hỏi bằng tiếng Việt
3. Chọn danh mục để thu hẹp phạm vi (tùy chọn)
4. Xem câu trả lời và tài liệu tham khảo

## 🔧 Cấu hình

### Environment Variables

```bash
# Database
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=legal_documents

# AI
OPENAI_API_KEY=your-openai-api-key-here
SENTENCE_TRANSFORMER_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Security
SECRET_KEY=your-super-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# File Upload
MAX_UPLOAD_SIZE=10485760  # 10MB
```

### AI Models

Hệ thống sử dụng:
- **Sentence-BERT**: `all-MiniLM-L6-v2` cho vector embedding
- **OpenAI GPT**: Cho Q&A (cần API key)

Nếu không có OpenAI API key, hệ thống sẽ dùng phương pháp fallback đơn giản.

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```

## 📁 Cấu trúc dự án

```
ths-csdl-nang-cao/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── routers/           # API endpoints
│   │   ├── models.py          # Pydantic models
│   │   ├── database.py        # MongoDB connection
│   │   ├── ai_service.py      # AI integration
│   │   └── document_processor.py  # File processing
│   ├── main.py                # FastAPI app
│   ├── requirements.txt       # Python dependencies
│   └── Dockerfile
├── frontend/                  # React Frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── pages/            # Page components
│   │   ├── services/         # API services
│   │   ├── types/            # TypeScript types
│   │   └── utils/            # Utility functions
│   ├── package.json
│   └── Dockerfile
├── scripts/                   # Setup scripts
│   └── init-mongo.js         # MongoDB initialization
├── docker-compose.yml        # Docker setup
└── README.md
```

## 🤝 Đóng góp

1. Fork repository
2. Tạo feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Tạo Pull Request

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

## 📞 Liên hệ

- **Author**: thanthienhai
- **Project Link**: https://github.com/thanthienhai/ths-csdl-nang-cao

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://reactjs.org/)
- [Material-UI](https://mui.com/)
- [MongoDB](https://www.mongodb.com/)
- [Sentence Transformers](https://www.sbert.net/)
- [OpenAI](https://openai.com/)