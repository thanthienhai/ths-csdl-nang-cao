#!/bin/bash

# Script to handle Docker Compose startup with better error handling
# This addresses network timeout issues and missing environment variables

echo "Starting Legal Documents Application..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found. Creating from template..."
    cp .env.example .env
    echo "Please edit .env file with your actual Gemini API key and credentials"
    exit 1
fi

# Set longer timeouts for Docker operations
export DOCKER_CLIENT_TIMEOUT=300
export COMPOSE_HTTP_TIMEOUT=300

echo "Stopping any existing containers..."
sudo docker-compose down

echo "Pulling required images with retries..."
for i in {1..3}; do
    echo "Attempt $i: Pulling MongoDB image..."
    if sudo docker pull mongo:7.0; then
        break
    fi
    echo "Pull failed, retrying in 10 seconds..."
    sleep 10
done

for i in {1..3}; do
    echo "Attempt $i: Pulling Python base image..."
    if sudo docker pull python:3.11-slim; then
        break
    fi
    echo "Pull failed, retrying in 10 seconds..."
    sleep 10
done

echo "Starting services..."
sudo -E docker-compose up -d

if [ $? -eq 0 ]; then
    echo "Services started successfully!"
    echo "Backend API: http://localhost:8000"
    echo "Frontend: http://localhost:3000"
    echo "MongoDB: localhost:27017"
else
    echo "Failed to start services. Check the logs:"
    sudo docker-compose logs
fi