# Use official Python image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project files
COPY . .

# Create required folders (in case not created by volume)
RUN mkdir -p /app/logs /app/output

# Expose port
EXPOSE 8000

# Use gunicorn for production (recommended over runserver)
CMD ["gunicorn", "bridgesec_data_transformer.wsgi:application", "--bind", "0.0.0.0:8000"]
