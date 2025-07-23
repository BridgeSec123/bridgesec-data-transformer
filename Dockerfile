FROM python:3.10-slim

# Install required system packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    supervisor \
 && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /bridgesec_data_transformer

# Install virtualenv
RUN pip install --upgrade pip && pip install virtualenv

# Create virtualenv inside the container
RUN virtualenv venv

# Activate virtualenv and install dependencies
COPY requirements.txt .
RUN . venv/bin/activate && pip install -r requirements.txt

# Copy project files
COPY bridgesec_data_transformer/ ./

# Collect static files (optional, or handled in supervisord later)
# RUN . venv/bin/activate && python manage.py collectstatic --noinput --settings=bridgesec_data_transformer.settings

# Set environment variable so supervisord uses virtualenv Python
ENV PATH="/bridgesec_data_transformer/venv/bin:$PATH"

# Copy supervisord config
COPY bridgesec_supervisord.conf /etc/supervisor/conf.d/bridgesec_supervisord.conf

RUN venv/bin/python manage.py collectstatic --noinput --settings=bridgesec_data_transformer.settings

# Create logs directory
RUN mkdir -p /bridgesec_data_transformer/logs \
 && chmod -R 755 /bridgesec_data_transformer/logs

EXPOSE 8000

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/bridgesec_supervisord.conf"]
