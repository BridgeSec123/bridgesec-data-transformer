import logging
import pika
import json
import os
import time


from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logging.getLogger("pika").setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def callback(ch, method, properties, body):
    message = json.loads(body)
    db = message.get("db_name")
    status = message.get("status")
    logger.info(f"Task finished for DB: {db}, status: {status}")
    
    ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    broker_url = os.getenv("CELERY_BROKER_URL")
    if not broker_url:
        raise Exception("CELERY_BROKER_URL is not set")

    parameters = pika.URLParameters(broker_url)

    logger.info(f"Publishing to: {broker_url}")

    while True:
        try:
            logger.info(f"Connecting to RabbitMQ at {broker_url}...")
            connection = pika.BlockingConnection(parameters)
            break
        except pika.exceptions.AMQPConnectionError:
            logger.info("RabbitMQ not ready yet. Retrying in 3 seconds...")
            time.sleep(3)

    channel = connection.channel()
    channel.queue_declare(queue="task_status", durable=True)
    channel.basic_consume(queue="task_status", on_message_callback=callback)

    logger.info("Waiting for task completion messages from Celery...")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Shutting down consumer...")
        channel.stop_consuming()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
