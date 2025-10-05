FROM python:3.11-slim

# Set environment variables to handle network timeouts
ENV PIP_DEFAULT_TIMEOUT=100
ENV PIP_RETRIES=3

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --timeout 100 --retries 3 -r requirements.txt

# Copy application code
COPY . .

# Create cache directory for AI models
RUN mkdir -p .cache

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]