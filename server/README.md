# THS Advanced Database - Backend Server

## Tổng quan (Overview)

Server backend được thiết kế cho môn học Cơ sở dữ liệu nâng cao với các tính năng:
- REST API endpoints
- Quản lý người dùng (User management)
- Quản lý sản phẩm và danh mục (Product & Category management)
- Cấu trúc modular dễ mở rộng

## Cấu trúc thư mục (Directory Structure)

```
server/
├── app/                    # Main application package
│   ├── __init__.py        # Flask app factory
│   ├── models/            # Database models
│   │   ├── __init__.py
│   │   ├── base.py        # Base model class
│   │   ├── user.py        # User model
│   │   └── product.py     # Product & Category models
│   ├── routes/            # API routes
│   │   ├── __init__.py
│   │   ├── api.py         # Main API blueprint
│   │   ├── users.py       # User endpoints
│   │   └── products.py    # Product endpoints
│   └── utils/             # Utility functions
│       ├── __init__.py
│       └── database.py    # Database utilities
├── config/                # Configuration files
│   ├── __init__.py
│   └── config.py          # App configuration
├── app.py                 # Main application entry point
├── requirements.txt       # Python dependencies
└── .env                   # Environment variables
```

## Cài đặt (Installation)

1. Tạo Python virtual environment:
```bash
cd server
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Cài đặt dependencies:
```bash
pip install -r requirements.txt
```

3. Khởi tạo database:
```bash
flask init-db
flask seed-db  # Tạo dữ liệu mẫu
```

4. Chạy server:
```bash
python app.py
```

Server sẽ chạy tại: http://localhost:5000

## API Endpoints

### Thông tin chung
- `GET /api/health` - Health check
- `GET /api/info` - API information

### Users
- `GET /api/users/` - Lấy danh sách users
- `GET /api/users/<id>` - Lấy thông tin user theo ID
- `POST /api/users/` - Tạo user mới
- `PUT /api/users/<id>` - Cập nhật user
- `DELETE /api/users/<id>` - Xóa user

### Products
- `GET /api/products/` - Lấy danh sách products
- `GET /api/products/<id>` - Lấy thông tin product theo ID
- `POST /api/products/` - Tạo product mới
- `PUT /api/products/<id>` - Cập nhật product
- `DELETE /api/products/<id>` - Xóa product

### Categories
- `GET /api/products/categories` - Lấy danh sách categories
- `POST /api/products/categories` - Tạo category mới

## Ví dụ sử dụng (Usage Examples)

### Tạo user mới:
```bash
curl -X POST http://localhost:5000/api/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "newuser@example.com",
    "full_name": "New User"
  }'
```

### Tạo product mới:
```bash
curl -X POST http://localhost:5000/api/products/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Product",
    "description": "Product description",
    "price": 99.99,
    "stock_quantity": 10,
    "category_id": 1
  }'
```

## Database Models

### User Model
- id (Integer, Primary Key)
- username (String, Unique)
- email (String, Unique)
- password_hash (String)
- full_name (String)
- is_active (Boolean)
- role (String)
- created_at (DateTime)
- updated_at (DateTime)

### Product Model
- id (Integer, Primary Key)
- name (String)
- description (Text)
- price (Numeric)
- stock_quantity (Integer)
- sku (String, Unique)
- is_active (Boolean)
- category_id (Foreign Key)
- created_at (DateTime)
- updated_at (DateTime)

### Category Model
- id (Integer, Primary Key)
- name (String)
- description (Text)
- is_active (Boolean)
- created_at (DateTime)
- updated_at (DateTime)

## Môi trường phát triển (Development)

### CLI Commands
- `flask init-db` - Khởi tạo database
- `flask seed-db` - Tạo dữ liệu mẫu
- `flask reset-db` - Reset database

### Configuration
Sửa file `.env` để thay đổi cấu hình:
- `FLASK_ENV` - development/production
- `SECRET_KEY` - Khóa bí mật
- `DEV_DATABASE_URL` - Database URL

## Mở rộng (Extensions)

Để thêm tính năng mới:
1. Tạo model trong `app/models/`
2. Tạo routes trong `app/routes/`
3. Register blueprint trong `app/routes/api.py`
4. Cập nhật database với `flask init-db`