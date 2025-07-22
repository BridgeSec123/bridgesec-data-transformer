FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    supervisor \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /bridgesec_data_transformer

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY bridgesec_data_transformer/ ./

RUN python manage.py collectstatic --noinput --settings=bridgesec_data_transformer.settings

COPY bridgesec_supervisord.conf /etc/supervisor/conf.d/bridgesec_supervisord.conf

RUN mkdir -p /bridgesec_data_transformer/logs \
 && chmod -R 755 /bridgesec_data_transformer/logs

EXPOSE 8000

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/bridgesec_supervisord.conf"]
