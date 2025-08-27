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

# Create and set permissions for temporary directories with more explicit setup
RUN mkdir -p /tmp /var/tmp /usr/tmp /app/tmp && \
    chmod 1777 /tmp /var/tmp /usr/tmp /app/tmp && \
    chown -R root:root /tmp /var/tmp /usr/tmp /app/tmp

# Create a startup script to ensure temp directories exist
RUN echo '#!/bin/bash\n\
mkdir -p /tmp /var/tmp /usr/tmp /app/tmp\n\
chmod 1777 /tmp /var/tmp /usr/tmp /app/tmp\n\
export TMPDIR=/tmp\n\
export TEMP=/tmp\n\
export TMP=/tmp\n\
exec gunicorn --bind 0.0.0.0:8000 --workers 4 --timeout 120 backend:app' > /app/start.sh && \
    chmod +x /app/start.sh

# Expose port
EXPOSE 8000

# Set environment variables
ENV FLASK_ENV=production
ENV PYTHONPATH=/app
ENV TMPDIR=/tmp
ENV TEMP=/tmp
ENV TMP=/tmp

# Run the application using the startup script
CMD ["/app/start.sh"]
