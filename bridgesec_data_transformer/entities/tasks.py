from core.tasks.bulk_tasks import run_bulk_entity_task
from core.utils.mongo_utils import get_dynamic_db
from rest_framework.response import Response
from rest_framework import status

def post(self, request):
    db_name = get_dynamic_db()

    # Trigger background task (no task_id anymore)
    run_bulk_entity_task.delay(db_name=db_name)

    return Response({
        "message": "Task triggered",
        "db_name": db_name,
    }, status=status.HTTP_202_ACCEPTED)
