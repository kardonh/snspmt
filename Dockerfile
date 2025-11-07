# Use a lightweight Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js from NodeSource (more reliable than curl)
RUN apt-get update && apt-get install -y curl \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Build frontend
RUN npm install && npm run build

# Make migration script executable
RUN chmod +x migrate_database.py

# Create directories for Flask and SQLite
RUN mkdir -p /app/logs && chmod 777 /app/logs
RUN mkdir -p /app/data && chmod 777 /app/data

# Expose port
EXPOSE 8000

# Set environment variables
ENV FLASK_ENV=production
ENV PYTHONPATH=/app

# Start the application with Gunicorn (respects PORT env on Render)
CMD ["sh", "-c", "python migrate_database.py && gunicorn backend:app --bind 0.0.0.0:${PORT:-8000} --workers 3 --timeout 120"]
