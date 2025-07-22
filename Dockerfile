FROM python:3.11-slim

WORKDIR /app

# Install system packages
RUN apt-get update && apt-get install -y supervisor && \
    mkdir -p /app/logs /app/output /var/log/supervisor

# Copy Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy entrypoint and supervisor config
COPY entrypoint.sh .
RUN dos2unix entrypoint.sh && chmod +x entrypoint.sh

COPY bridgesec_supervisord.conf /etc/supervisor/conf.d/bridgesec_supervisord.conf

# Copy app source
COPY . .

# Default command
CMD ["./entrypoint.sh"]
