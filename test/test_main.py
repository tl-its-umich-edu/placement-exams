# standard libraries
import json, os
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

# third-party libraries
from django.core import mail
from django.db.models import QuerySet
from django.test import TestCase
from requests import Response
from umich_api.api_utils import ApiUtil

# local libraries
from constants import API_FIXTURES_DIR, ROOT_DIR
from pe.main import main
from pe.models import Report


class MainTestCase(TestCase):
    fixtures: List[str] = ['test_03.json']

    def setUp(self):
        """
        Initializes api_handler and API response data used for patching.
        """
        self.api_handler: ApiUtil = ApiUtil(
            os.getenv('API_DIR_URL', ''),
            os.getenv('API_DIR_CLIENT_ID', ''),
            os.getenv('API_DIR_SECRET', ''),
            os.path.join(ROOT_DIR, 'config', 'apis.json')
        )

        with open(os.path.join(API_FIXTURES_DIR, 'canvas_subs.json'), 'r') as test_canvas_subs_file:
            canvas_subs_dict: Dict[str, List[Dict[str, Any]]] = json.loads(test_canvas_subs_file.read())

        self.canvas_dada_place_subs: List[Dict[str, Any]] = canvas_subs_dict['DADA_Placement_1']

        with open(os.path.join(API_FIXTURES_DIR, 'mpathways_resp_data.json'), 'r') as mpathways_resp_data_file:
            self.mpathways_resp_data: List[Dict[str, Any]] = json.loads(mpathways_resp_data_file.read())

    def test_main(self):
        """
        Function main successfully uses ScoresOrchestration and Reporter classes to collect, transmit, and
        report by email on new exam submissions.
        """
        with patch('pe.orchestration.api_call_with_retries', autospec=True) as mock_get:
            with patch.object(ApiUtil, 'api_call', autospec=True) as mock_send:
                mock_get.return_value = MagicMock(
                    spec=Response, status_code=200, text=json.dumps(self.canvas_dada_place_subs)
                )
                mock_send.return_value = MagicMock(
                    spec=Response, status_code=200, text=json.dumps(self.mpathways_resp_data[7])
                )
                main(self.api_handler)

        dada_report: Report = Report.objects.get(id=3)
        new_submissions_qs: QuerySet = dada_report.exams.first().submissions.all()
        self.assertEqual(
            list(new_submissions_qs.values('student_uniqname', 'score', 'transmitted')),
            [{'student_uniqname': 'nlongbottom', 'score': 500.0, 'transmitted': True}]
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_main_does_not_send_email_when_no_transmission_activity(self):
        """
        Function main does not send email when there are no successful or failed transmissions.
        (Note this also implies that there were no new submissions found.)
        """
        with patch('pe.orchestration.api_call_with_retries', autospec=True) as mock_get:
            mock_get.return_value = MagicMock(spec=Response, status_code=200, text=json.dumps([]))
            main(self.api_handler)

        dada_report: Report = Report.objects.get(id=3)
        new_submissions_qs: QuerySet = dada_report.exams.first().submissions.all()
        self.assertFalse(new_submissions_qs.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_main_sends_email_when_only_transmission_failures(self):
        """
        Function main still sends email when there are failed transmissions.
        """
        with patch('pe.orchestration.api_call_with_retries', autospec=True) as mock_get:
            with patch.object(ApiUtil, 'api_call', autospec=True) as mock_send:
                mock_get.return_value = MagicMock(
                    spec=Response, status_code=200, text=json.dumps(self.canvas_dada_place_subs)
                )
                mock_send.return_value = MagicMock(spec=Response, status_code=500, text=json.dumps({}))
                main(self.api_handler)

        dada_report: Report = Report.objects.get(id=3)
        failed_submissions_qs: QuerySet = dada_report.exams.first().submissions.filter(transmitted=False)
        self.assertTrue(len(failed_submissions_qs), 2)
        self.assertEqual(len(mail.outbox), 1)
