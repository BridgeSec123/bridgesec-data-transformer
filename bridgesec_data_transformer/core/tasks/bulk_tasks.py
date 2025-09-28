from celery import shared_task
from core.utils.mongo_utils import ensure_mongo_connection, get_dynamic_db
from django.conf import settings
from entities.registry import ENTITY_VIEWSETS
import os
import json
import logging
import pika

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def notify_backend_via_rabbitmq(db_name):
    try:
        broker_url = os.getenv("CELERY_BROKER_URL")
        logger.info(f"Connecting to broker: {broker_url}")
        connection = pika.BlockingConnection(pika.URLParameters(broker_url))
        channel = connection.channel()

        channel.queue_declare(queue="task_status", durable=True)
        message = json.dumps({"db_name": db_name, "status": "completed"})

        logger.info(f"Sending message to 'task_status': {message}")
        channel.basic_publish(
            exchange="",
            routing_key="task_status",
            body=message,
            properties=pika.BasicProperties(delivery_mode=2),
        )

        logger.info(f"Status message for DB {db_name} sent.")
        connection.close()

    except Exception as e:
        logger.exception(f"Failed to notify via RabbitMQ: {e}")


@shared_task
def run_bulk_entity_task():
    db_name = get_dynamic_db()
    logger.info(f"[TASK START] run_bulk_entity_task triggered with db_name={db_name}")

    try:
        # Ensure MongoDB connection
        ensure_mongo_connection(db_name)
        logger.info(f"MongoDB connection established for db_name={db_name}")

        # Process each entity
        for entity_name, viewset_class in ENTITY_VIEWSETS.items():
            logger.info(f"Processing entity: {entity_name}")
            viewset_instance = viewset_class()
            extracted_data = viewset_instance.fetch_and_store_data(db_name)

            if not extracted_data:
                logger.error(f"Failed to fetch {entity_name} data")
                continue

            # Create output directory
            output_dir = os.path.join(settings.BASE_DIR, "output", db_name)
            os.makedirs(output_dir, exist_ok=True)

            # Save data to JSON files
            for sub_entity_name, sub_entity_data in extracted_data.items():
                file_name = f"{sub_entity_name}.json"
                file_path = os.path.join(output_dir, file_name)

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(sub_entity_data, f, ensure_ascii=False, indent=4)

                logger.info(f"Saved {sub_entity_name} data to {file_path}")

        logger.info(f"[TASK COMPLETED] All data stored for DB: {db_name}")
        notify_backend_via_rabbitmq(db_name)
        return {"status": "success", "db_name": db_name}

    except Exception as e:
        logger.exception(f"Error during bulk entity fetch for db {db_name}: {e}")
        return {"status": "error", "db_name": db_name, "error": str(e)}
