from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .tasks import run_bulk_task

class BulkTriggerView(APIView):
    def post(self, request):
        run_bulk_task.delay()  # No task_id
        return Response({
            "message": "Task triggered"
        }, status=status.HTTP_202_ACCEPTED)
