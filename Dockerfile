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

# Create temp directories with proper permissions
RUN mkdir -p /tmp && chmod 777 /tmp
RUN mkdir -p /app/tmp && chmod 777 /app/tmp
RUN mkdir -p /usr/tmp && chmod 777 /usr/tmp
RUN mkdir -p /var/tmp && chmod 777 /var/tmp

# Create writable directories for Gunicorn
RUN mkdir -p /app/var && chmod 777 /app/var
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Expose port
EXPOSE 8000

# Set environment variables
ENV FLASK_ENV=production
ENV PYTHONPATH=/app
ENV TMPDIR=/app/var
ENV TEMP=/app/var
ENV TMP=/app/var
ENV TEMP_DIR=/app/var

# Run the application with Gunicorn production server
CMD ["gunicorn", "--config", "gunicorn.conf.py", "backend:app"]
