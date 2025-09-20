# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

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

# Run the application with Flask development server (final solution for read-only filesystem)
CMD ["python", "-c", "from backend import app; app.run(host='0.0.0.0', port=8000, debug=False, threaded=True)"]
