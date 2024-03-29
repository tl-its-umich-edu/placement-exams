# standard libraries
import json, logging, os
from datetime import datetime
from typing import Any, Union
from unittest.mock import MagicMock, patch

# third-party libraries
from django.test import TestCase
from django.utils.timezone import utc
from requests import Response
from umich_api.api_utils import ApiUtil

# Local libraries
from api_retry.util import api_call_with_retries, check_if_response_successful
from constants import API_FIXTURES_DIR, CANVAS_SCOPE, CANVAS_URL_BEGIN, ISO8601_FORMAT, ROOT_DIR


LOGGER = logging.getLogger(__name__)


class TestApiRetry(TestCase):

    def setUp(self):
        """Set up ApiUtil instance and data needed by test methods."""
        self.api_handler: ApiUtil = ApiUtil(
            os.getenv('API_DIR_URL', ''),
            os.getenv('API_DIR_CLIENT_ID', ''),
            os.getenv('API_DIR_SECRET', ''),
            os.path.join(ROOT_DIR, 'config', 'apis.json')
        )

        with open(os.path.join(API_FIXTURES_DIR, 'canvas_subs.json'), 'r') as test_canvas_subs_file:
            canvas_subs_dict: dict[str, list[dict[str, Any]]] = json.loads(test_canvas_subs_file.read())

        self.canvas_potions_val_subs: list[dict[str, Any]] = canvas_subs_dict['Potions_Validation_1']

        # "Potions Validation" from test_04.json
        some_course_id: int = 888888
        some_assignment_id: int = 111112
        some_filter: datetime = datetime(2020, 6, 1, 0, 0, 0, tzinfo=utc)

        self.get_scores_url: str = (
            f'{CANVAS_URL_BEGIN}/courses/{some_course_id}/students/submissions'
        )

        self.canvas_params: dict[str, Any] = {
            'student_ids': ['all'],
            'assignment_ids': [str(some_assignment_id)],
            'per_page': '50',
            'include': ['user'],
            'graded_since': some_filter.strftime(ISO8601_FORMAT)
        }

    def test_check_if_response_successful_when_valid(self):
        """check_if_response_successful returns True with a valid Response."""
        response: MagicMock = MagicMock(
            spec=Response,
            status_code=200,
            text=json.dumps(self.canvas_potions_val_subs),
            url=self.get_scores_url
        )
        result: bool = check_if_response_successful(response)
        self.assertTrue(result)

    def test_check_if_response_successful_with_irregular_code(self):
        """check_if_response_successful returns False if Response has an irregular status code."""
        response: MagicMock = MagicMock(
            spec=Response,
            status_code=404,
            text=json.dumps({'message': 'No data was found for specified URL and parameters.'}),
            url='blahblahblah'
        )
        result: bool = check_if_response_successful(response)
        self.assertFalse(result)

    def test_check_if_response_successful_with_invalid_json(self):
        """check_if_response_successful returns False if Response has invalid JSON in text variable."""
        response: MagicMock = MagicMock(
            spec=Response,
            status_code=200,
            text=json.dumps(self.canvas_potions_val_subs)[:20],  # Trims ending of JSON string.
            url=self.get_scores_url
        )
        result: bool = check_if_response_successful(response)
        self.assertFalse(result)

    def test_api_call_with_retries_when_no_errors(self):
        """api_call_with_retries returns Response object when a valid Response is found."""

        with patch.object(ApiUtil, 'api_call', autospec=True) as mock_api_call:
            mock_api_call.return_value = MagicMock(
                spec=Response,
                status_code=200,
                text=json.dumps(self.canvas_potions_val_subs),
                url='/'.join([self.api_handler.base_url, self.get_scores_url])
            )

            response = api_call_with_retries(
                self.api_handler,
                self.get_scores_url,
                CANVAS_SCOPE,
                'GET',
                self.canvas_params
            )

        self.assertEqual(mock_api_call.call_count, 1)
        mock_api_call.assert_called_with(self.api_handler, self.get_scores_url, CANVAS_SCOPE, 'GET', self.canvas_params)
        self.assertTrue(response.ok)
        self.assertEqual(json.loads(response.text), self.canvas_potions_val_subs)

    def test_api_call_with_retries_with_all_errors(self):
        """api_call_with_retries returns None when no valid Response is found after the maximum number of attempts."""
        full_url: str = '/'.join([self.api_handler.base_url, self.get_scores_url])
        num_attempts: int = 4
        resp_mocks: list[MagicMock] = [
            MagicMock(
                spec=Response, status_code=504, text=json.dumps({'message': 'Gateway Timeout'}), url=full_url
            )
            for i in range(num_attempts + 1)
        ]

        with patch.object(ApiUtil, 'api_call', autospec=True) as mock_api_call:
            mock_api_call.side_effect = resp_mocks

            response: Union[MagicMock, None] = api_call_with_retries(
                self.api_handler,
                self.get_scores_url,
                CANVAS_SCOPE,
                'GET',
                self.canvas_params,
                max_req_attempts=num_attempts
            )

        self.assertEqual(mock_api_call.call_count, 4)
        mock_api_call.assert_called_with(self.api_handler, self.get_scores_url, CANVAS_SCOPE, 'GET', self.canvas_params)
        self.assertEqual(response, None)
