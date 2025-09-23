#!/bin/bash

echo "🧪 Testing Legal Document Search System..."

# Test backend Python syntax
echo "📝 Testing backend Python syntax..."
cd backend
if python -m py_compile main.py app/*.py app/routers/*.py; then
    echo "✅ Backend Python syntax is valid"
else
    echo "❌ Backend Python syntax errors found"
    exit 1
fi

# Test frontend package.json
echo "📦 Testing frontend package.json..."
cd ../frontend
if node -e "JSON.parse(require('fs').readFileSync('package.json', 'utf8'))"; then
    echo "✅ Frontend package.json is valid"
else
    echo "❌ Frontend package.json is invalid"
    exit 1
fi

# Test Docker Compose configuration
echo "🐳 Testing Docker Compose configuration..."
cd ..
if docker-compose config >/dev/null 2>&1; then
    echo "✅ Docker Compose configuration is valid"
else
    echo "❌ Docker Compose configuration is invalid"
    exit 1
fi

echo ""
echo "🎉 All tests passed!"
echo ""
echo "🚀 To start the system:"
echo "   ./start.sh"