FROM python:3.11-slim

WORKDIR /app

# Install system packages
RUN apt-get update && apt-get install -y supervisor && \
    mkdir -p /app/logs /app/output /var/log/supervisor

# Copy Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the full app
COPY . .

# Copy your supervisor config into the correct folder
COPY bridgesec_supervisord.conf /etc/supervisor/conf.d/bridgesec_supervisord.conf

# Start supervisor
CMD ["/usr/bin/supervisord", "-n"]
