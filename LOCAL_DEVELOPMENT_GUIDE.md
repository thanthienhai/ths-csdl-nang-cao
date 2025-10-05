# 🎯 Local Frontend Development Setup

## 📋 **Overview**
This setup runs:
- ✅ **MongoDB + Backend**: In Docker containers  
- 🎨 **Frontend**: Locally for easier debugging

## 🚀 **Quick Start**

### Option 1: Automated Setup
```bash
cd /home/ubuntu/Coding/ths-csdl-nang-cao
./setup-local-dev.sh
```

### Option 2: Manual Setup

#### Step 1: Start Backend Services
```bash
cd /home/ubuntu/Coding/ths-csdl-nang-cao
sudo docker-compose up -d mongodb backend
```

#### Step 2: Set up Frontend Environment
```bash
cd frontend

# Create local environment file
cat > .env.local << EOF
REACT_APP_API_URL=http://localhost:8000/api
GENERATE_SOURCEMAP=false
BROWSER=none
EOF

# Install dependencies
npm install --legacy-peer-deps
```

#### Step 3: Start Frontend
```bash
# In frontend directory
npm start
```

## 🔍 **Service URLs**
- **MongoDB**: `mongodb://localhost:27017`
- **Backend API**: `http://localhost:8000`
- **API Docs**: `http://localhost:8000/docs`
- **Frontend**: `http://localhost:3000`

## 🛠 **Development Commands**

### Backend Services
```bash
# Start only backend services
sudo docker-compose up -d mongodb backend

# View backend logs
sudo docker-compose logs backend -f

# Restart backend
sudo docker-compose restart backend

# Stop all services
sudo docker-compose down
```

### Frontend Development
```bash
cd frontend

# Start development server
npm start

# Build for production
npm run build

# Run tests
npm test

# Install new packages
npm install package-name --save
```

## 🐛 **Debugging & Troubleshooting**

### Common Issues

#### 1. API Connection Failed
**Problem**: Frontend can't connect to backend
**Solution**: 
```bash
# Check if backend is running
curl http://localhost:8000/health

# Check backend logs
sudo docker-compose logs backend
```

#### 2. MongoDB Connection Issues
**Problem**: Backend can't connect to MongoDB
**Solution**:
```bash
# Check MongoDB status
sudo docker-compose logs mongodb

# Restart MongoDB
sudo docker-compose restart mongodb
```

#### 3. Frontend Dependency Issues
**Problem**: npm install fails
**Solution**:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install --legacy-peer-deps
```

#### 4. Port Already in Use
**Problem**: Port 3000/8000 occupied
**Solution**:
```bash
# Kill processes on port 3000
sudo lsof -t -i:3000 | xargs sudo kill -9

# Kill processes on port 8000
sudo lsof -t -i:8000 | xargs sudo kill -9
```

## 🔄 **Development Workflow**

### 1. Daily Development
```bash
# Morning startup
./setup-local-dev.sh

# Work on frontend (in new terminal)
cd frontend
npm start

# Work on backend (edit files, container auto-reloads)
```

### 2. Testing API Changes
```bash
# Test individual endpoints
curl -X GET "http://localhost:8000/api/documents/"

# Test file upload
curl -X POST "http://localhost:8000/api/documents/upload" \
  -F "file=@test.txt" \
  -F "title=Test Document" \
  -F "category=test"
```

### 3. Environment Variables

#### Backend (.env)
```env
MONGODB_URL=mongodb://admin:password123@localhost:27017/legal_documents?authSource=admin
DATABASE_NAME=legal_documents
GEMINI_API_KEY=your_gemini_api_key
```

#### Frontend (.env.local)
```env
REACT_APP_API_URL=http://localhost:8000/api
GENERATE_SOURCEMAP=false
BROWSER=none
```

## 📊 **Performance Benefits**

### Local Frontend Advantages:
- ⚡ **Faster Hot Reload**: Instant code changes
- 🐛 **Better Debugging**: Full browser dev tools
- 📝 **Real-time Logs**: See errors immediately
- 🎨 **Live Development**: No container rebuilds

### Docker Backend Advantages:
- 🔒 **Consistent Environment**: Same as production
- 📦 **Easy Database**: MongoDB ready to use
- 🔄 **Auto-restart**: Code changes reload automatically
- 🚀 **Simple Deployment**: Same container for production

## 🎉 **Success Indicators**

When everything is working correctly:
- ✅ `sudo docker-compose ps` shows 2 containers running
- ✅ `http://localhost:8000/health` returns `{"status": "healthy"}`
- ✅ `http://localhost:3000` loads the React app
- ✅ Frontend can call backend APIs successfully
- ✅ No CORS errors in browser console

## 🔧 **Advanced Configuration**

### Custom API Base URL
```javascript
// In frontend/src/services/api.ts
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api',
});
```

### Backend Hot Reload
```yaml
# docker-compose.yml already configured for:
volumes:
  - ./backend:/app  # Auto-reload on file changes
```

This setup gives you the best of both worlds: stable containerized backend services with flexible local frontend development! 🚀