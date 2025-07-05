from celery import shared_task
from core.utils.mongo_utils import ensure_mongo_connection
from django.conf import settings
from entities.registry import ENTITY_VIEWSETS
import os
import json
import logging
import pika
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def notify_backend_via_rabbitmq(db_name):
    broker_url = os.getenv("CELERY_BROKER_URL")
    print(f"[🔗] Connecting to broker: {broker_url}")
    connection = pika.BlockingConnection(pika.URLParameters(broker_url))
    channel = connection.channel()

    channel.queue_declare(queue="task_status", durable=True)
    message = json.dumps({"db_name": db_name, "status": "completed"})

    print(f"[📤] Sending message to 'task_status': {message}")
    channel.basic_publish(
        exchange="",
        routing_key="task_status",
        body=message,
        properties=pika.BasicProperties(delivery_mode=2),
    )

    print(f"[✔] Status message for DB {db_name} sent.")
    connection.close()

@shared_task
def run_bulk_entity_task(db_name, task_id=None):
    try:
        ensure_mongo_connection(db_name)

        for entity_name, viewset_class in ENTITY_VIEWSETS.items():
            viewset_instance = viewset_class()
            extracted_data = viewset_instance.fetch_and_store_data(db_name)

            if not extracted_data:
                logger.error(f"[{task_id}] Failed to fetch {entity_name} data")
                continue

            output_dir = os.path.join(settings.BASE_DIR, "output", db_name)
            os.makedirs(output_dir, exist_ok=True)

            for sub_entity_name, sub_entity_data in extracted_data.items():
                file_name = f"{sub_entity_name}.json"
                file_path = os.path.join(output_dir, file_name)

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(sub_entity_data, f, ensure_ascii=False, indent=4)

        logger.info(f"[{task_id}] Data stored for DB: {db_name}")

        # TODO: Notify frontend via WebSocket here (Django Channels etc.)

    except Exception as e:
        logger.exception(f"[{task_id}] Error during bulk entity fetch: {str(e)}")

    notify_backend_via_rabbitmq(db_name)