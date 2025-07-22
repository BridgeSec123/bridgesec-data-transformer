
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN mkdir -p /app/logs /app/output

# Add entrypoints for different services via argument
ARG SERVICE

# Default to gunicorn
CMD if [ "$SERVICE" = "celery" ]; then \
      celery -A bridgesec_data_transformer worker --loglevel=INFO 2>&1 | tee -a /app/logs/app.log ; \
    elif [ "$SERVICE" = "consumer" ]; then \
      python core/rabbitmq_consumer.py ; \
    else \
      gunicorn bridgesec_data_transformer.wsgi:application \
        --chdir bridgesec_data_transformer \
        --bind 0.0.0.0:8000 \
        --timeout 2000 ; \
    fi
