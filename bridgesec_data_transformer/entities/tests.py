from unittest.mock import MagicMock, patch, call
from django.test import TestCase
from rest_framework.test import APIRequestFactory
from rest_framework import status

from entities.views.confirm_delete_view import ConfirmDeletionView


# ---------------------------------------------------------------------------
# Sample plan document (mirrors what restore_utils.create_deletion_plan stores)
# ---------------------------------------------------------------------------

_PLAN_DOC = {
    "db_name": "bridgesec_2026-03-10T0357",
    "entity_name": "Policy MFA",
    "collection_name": "okta_policy_mfa",
    "id_field": "id",
    "complete_deleted_records": [{"id": "pol123", "name": "MFA Policy"}],
    "merged_data": [{"id": "pol456", "name": "Other Policy"}],
    "terraform_params": {
        "collection_name": "okta_policy_mfa",
        "target_id": "pol123",
        "operation": "delete",
    },
    "terraform_url": "http://oktf-service/api/",
    "cascade_info": {},
}


# ---------------------------------------------------------------------------
# Tests: ConfirmDeletionView (confirm_delete_view.py)
# ---------------------------------------------------------------------------

class TestConfirmDeletionView(TestCase):
    """
    Tests for the Phase 2 confirm-delete endpoint.

    All external dependencies (MongoDB, OkTf HTTP call, authentication)
    are mocked so tests run in isolation without live infrastructure.
    """

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = ConfirmDeletionView.as_view()

    def _make_request(self):
        return self.factory.post('/confirm-delete/abc123/', format='json')

    def _run_view(self, request, plan_id='abc123'):
        """Call the view bypassing authentication/permission checks."""
        with patch.object(ConfirmDeletionView, 'authentication_classes', []), \
             patch.object(ConfirmDeletionView, 'permission_classes', []):
            return self.view(request, plan_id=plan_id)

    # ------------------------------------------------------------------
    # Plan validation failures
    # ------------------------------------------------------------------

    @patch('entities.views.confirm_delete_view.get_user_from_request', return_value='testuser')
    @patch('entities.views.confirm_delete_view.mongo_client', MagicMock())
    @patch('entities.views.confirm_delete_view.load_deletion_plan')
    def test_plan_not_found_returns_404(self, mock_load, _):
        mock_load.return_value = (
            None,
            {'status': status.HTTP_404_NOT_FOUND, 'error': 'Plan not found'},
        )
        response = self._run_view(self._make_request())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)

    @patch('entities.views.confirm_delete_view.get_user_from_request', return_value='testuser')
    @patch('entities.views.confirm_delete_view.mongo_client', MagicMock())
    @patch('entities.views.confirm_delete_view.load_deletion_plan')
    def test_expired_plan_returns_410(self, mock_load, _):
        mock_load.return_value = (
            None,
            {'status': status.HTTP_410_GONE, 'error': 'Plan has expired'},
        )
        response = self._run_view(self._make_request())
        self.assertEqual(response.status_code, status.HTTP_410_GONE)

    @patch('entities.views.confirm_delete_view.get_user_from_request', return_value='testuser')
    @patch('entities.views.confirm_delete_view.mongo_client', MagicMock())
    @patch('entities.views.confirm_delete_view.load_deletion_plan')
    def test_already_applied_plan_returns_409(self, mock_load, _):
        mock_load.return_value = (
            None,
            {'status': status.HTTP_409_CONFLICT, 'error': 'Plan already applied'},
        )
        response = self._run_view(self._make_request())
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    # ------------------------------------------------------------------
    # Successful deletion (OkTf returns 2xx)
    # ------------------------------------------------------------------

    @patch('entities.views.confirm_delete_view.verify_deletion_complete', return_value={'verified': True})
    @patch('entities.views.confirm_delete_view.update_deletion_status')
    @patch('entities.views.confirm_delete_view.mark_plan_applied')
    @patch('entities.views.confirm_delete_view.ensure_mongo_connection')
    @patch('entities.views.confirm_delete_view.get_okta_headers', return_value={})
    @patch('entities.views.confirm_delete_view.get_user_from_request', return_value='testuser')
    @patch('entities.views.confirm_delete_view.mongo_client', MagicMock())
    @patch('entities.views.confirm_delete_view.load_deletion_plan')
    @patch('entities.views.confirm_delete_view.requests')
    def test_successful_okta_call_returns_200_with_deleted_ids(
        self, mock_requests, mock_load, mock_user, mock_headers,
        mock_ensure, mock_mark, mock_update, mock_verify,
    ):
        mock_load.return_value = (_PLAN_DOC, None)

        mock_tf_resp = MagicMock()
        mock_tf_resp.status_code = 200
        mock_tf_resp.json.return_value = {
            'message': 'Successfully deleted 1 resource(s) from Okta',
            'deleted_targets': ['module.okta_policy_mfa["pol123"]'],
        }
        mock_requests.post.return_value = mock_tf_resp

        response = self._run_view(self._make_request())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('deleted_ids', response.data)
        self.assertEqual(response.data['deleted_ids'], ['pol123'])
        self.assertIn('tf_message', response.data)
        self.assertIn('verification', response.data)

    @patch('entities.views.confirm_delete_view.verify_deletion_complete', return_value={'verified': True})
    @patch('entities.views.confirm_delete_view.update_deletion_status')
    @patch('entities.views.confirm_delete_view.mark_plan_applied')
    @patch('entities.views.confirm_delete_view.ensure_mongo_connection')
    @patch('entities.views.confirm_delete_view.get_okta_headers', return_value={})
    @patch('entities.views.confirm_delete_view.get_user_from_request', return_value='testuser')
    @patch('entities.views.confirm_delete_view.mongo_client', MagicMock())
    @patch('entities.views.confirm_delete_view.load_deletion_plan')
    @patch('entities.views.confirm_delete_view.requests')
    def test_success_updates_status_to_deleted(
        self, mock_requests, mock_load, mock_user, mock_headers,
        mock_ensure, mock_mark, mock_update, mock_verify,
    ):
        mock_load.return_value = (_PLAN_DOC, None)

        mock_tf_resp = MagicMock()
        mock_tf_resp.status_code = 200
        mock_tf_resp.json.return_value = {'message': 'ok'}
        mock_requests.post.return_value = mock_tf_resp

        self._run_view(self._make_request())

        # First call is for parent records
        parent_call_kwargs = mock_update.call_args_list[0][1]
        self.assertEqual(parent_call_kwargs['new_status'], 'deleted')

    # ------------------------------------------------------------------
    # Failed deletion (OkTf returns 5xx)
    # ------------------------------------------------------------------

    @patch('entities.views.confirm_delete_view.update_deletion_status')
    @patch('entities.views.confirm_delete_view.mark_plan_applied')
    @patch('entities.views.confirm_delete_view.ensure_mongo_connection')
    @patch('entities.views.confirm_delete_view.get_okta_headers', return_value={})
    @patch('entities.views.confirm_delete_view.get_user_from_request', return_value='testuser')
    @patch('entities.views.confirm_delete_view.mongo_client', MagicMock())
    @patch('entities.views.confirm_delete_view.load_deletion_plan')
    @patch('entities.views.confirm_delete_view.requests')
    def test_okta_failure_returns_500_and_marks_deletion_failed(
        self, mock_requests, mock_load, mock_user, mock_headers,
        mock_ensure, mock_mark, mock_update,
    ):
        mock_load.return_value = (_PLAN_DOC, None)

        mock_tf_resp = MagicMock()
        mock_tf_resp.status_code = 500
        mock_tf_resp.json.return_value = {'error': 'Terraform destroy failed'}
        mock_requests.post.return_value = mock_tf_resp

        response = self._run_view(self._make_request())

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('error', response.data)

        parent_call_kwargs = mock_update.call_args_list[0][1]
        self.assertEqual(parent_call_kwargs['new_status'], 'deletion_failed')

    # ------------------------------------------------------------------
    # Race-condition guard: mark_plan_applied before OkTf call
    # ------------------------------------------------------------------

    @patch('entities.views.confirm_delete_view.verify_deletion_complete', return_value={'verified': True})
    @patch('entities.views.confirm_delete_view.update_deletion_status')
    @patch('entities.views.confirm_delete_view.ensure_mongo_connection')
    @patch('entities.views.confirm_delete_view.get_okta_headers', return_value={})
    @patch('entities.views.confirm_delete_view.get_user_from_request', return_value='testuser')
    @patch('entities.views.confirm_delete_view.mongo_client', MagicMock())
    @patch('entities.views.confirm_delete_view.load_deletion_plan')
    def test_mark_plan_applied_is_called_before_okta_http_request(
        self, mock_load, mock_user, mock_headers, mock_ensure, mock_update, mock_verify,
    ):
        """Race-condition guard: plan must be marked 'applied' before OkTf is called."""
        mock_load.return_value = (_PLAN_DOC, None)
        call_order = []

        with patch('entities.views.confirm_delete_view.mark_plan_applied',
                   side_effect=lambda *a, **kw: call_order.append('mark_applied')):
            with patch('entities.views.confirm_delete_view.requests') as mock_requests:
                mock_tf_resp = MagicMock()
                mock_tf_resp.status_code = 200
                mock_tf_resp.json.return_value = {'message': 'ok'}
                mock_requests.post.side_effect = (
                    lambda *a, **kw: (call_order.append('okta_call'), mock_tf_resp)[1]
                )
                self._run_view(self._make_request())

        self.assertIn('mark_applied', call_order)
        self.assertIn('okta_call', call_order)
        self.assertLess(
            call_order.index('mark_applied'),
            call_order.index('okta_call'),
            msg="mark_plan_applied must be called BEFORE the OkTf HTTP request",
        )
