# Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy code
COPY . .

# Make sure log directories exist
RUN mkdir -p /app/logs /app/output

# No CMD or ENTRYPOINT here — Render uses startCommand
