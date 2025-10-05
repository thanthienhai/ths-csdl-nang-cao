#!/bin/bash

# Local Frontend Development Setup Script
# This script sets up the environment to run frontend locally with Docker backend

echo "🚀 Setting up Local Frontend Development Environment"
echo "=================================================="

# Step 1: Start only backend services with Docker
echo "📦 Starting MongoDB and Backend services..."
cd /home/ubuntu/Coding/ths-csdl-nang-cao
sudo docker-compose up -d mongodb backend

echo "⏳ Waiting for services to start..."
sleep 10

# Step 2: Check if services are running
echo "🔍 Checking Docker services status..."
sudo docker-compose ps

# Step 3: Set up frontend environment
echo "🎨 Setting up Frontend environment..."
cd frontend

# Create .env file for local development
cat > .env.local << EOF
REACT_APP_API_URL=http://localhost:8000/api
GENERATE_SOURCEMAP=false
BROWSER=none
EOF

# Step 4: Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install --legacy-peer-deps
else
    echo "✅ Frontend dependencies already installed"
fi

echo ""
echo "🎉 Setup Complete!"
echo "==================="
echo ""
echo "🔧 Services Status:"
echo "  ✅ MongoDB: http://localhost:27017"
echo "  ✅ Backend API: http://localhost:8000"
echo "  🎨 Frontend: Ready to start locally"
echo ""
echo "🚀 To start the frontend:"
echo "  cd frontend"
echo "  npm start"
echo ""
echo "🔍 To check backend logs:"
echo "  sudo docker-compose logs backend -f"
echo ""
echo "🛑 To stop Docker services:"
echo "  sudo docker-compose down"
echo ""