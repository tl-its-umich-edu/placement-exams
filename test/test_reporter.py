# standard libraries
import json, logging, os
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

# third-party libraries
from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.test import TestCase
from django.utils.timezone import utc
from requests import Response
from umich_api.api_utils import ApiUtil

# local libraries
from constants import API_FIXTURES_DIR, ROOT_DIR, SNAPSHOTS_DIR
from pe.models import Report
from pe.orchestration import ScoresOrchestration
from pe.reporter import Reporter


LOGGER = logging.getLogger(__name__)


class ReporterTestCase(TestCase):
    fixtures: list[str] = ['test_01.json', 'test_04.json']

    def setUp(self):
        """
        Initializes report; runs orchestrations, gathering time metadata; and sets up other shared variables.
        """
        api_handler: ApiUtil = ApiUtil(
            os.getenv('API_DIR_URL', ''),
            os.getenv('API_DIR_CLIENT_ID', ''),
            os.getenv('API_DIR_SECRET', ''),
            os.path.join(ROOT_DIR, 'config', 'apis.json')
        )

        with open(os.path.join(API_FIXTURES_DIR, 'canvas_subs.json'), 'r') as test_canvas_subs_file:
            canvas_subs_dict: dict[str, list[dict[str, Any]]] = json.loads(test_canvas_subs_file.read())

        canvas_potions_val_subs: list[dict[str, Any]] = canvas_subs_dict['Potions_Validation_1']

        with open(os.path.join(API_FIXTURES_DIR, 'mpathways_resp_data.json'), 'r') as mpathways_resp_data_file:
            mpathways_resp_data: list[dict[str, Any]] = json.loads(mpathways_resp_data_file.read())

        self.potions_report = Report.objects.get(id=1)

        with patch('pe.orchestration.api_call_with_retries', autospec=True) as mock_get:
            with patch.object(ApiUtil, 'api_call', autospec=True) as mock_send:
                mock_get.side_effect = [
                    # Potions Placement - no more new submissions
                    MagicMock(spec=Response, status_code=200, text=json.dumps([])),
                    # Potions Validation - two more new submissions
                    MagicMock(spec=Response, status_code=200, text=json.dumps(canvas_potions_val_subs))
                ]
                mock_send.side_effect = [
                    # Potions Placement - Only rweasley sub from test_04.json, fails to send
                    MagicMock(spec=Response, status_code=200, text=json.dumps(mpathways_resp_data[5])),
                    # Potions Validation - Four subs, two from canvas_subs.json, two from test_04.json, all send
                    MagicMock(spec=Response, status_code=200, text=json.dumps(mpathways_resp_data[2]))
                ]

                fake_running_dt: datetime = datetime(2020, 6, 25, 16, 0, 0, tzinfo=utc)
                self.exams_time_metadata: dict[int, dict[str, datetime]] = dict()
                for exam in self.potions_report.exams.all():
                    start: datetime = fake_running_dt
                    exam_orca: ScoresOrchestration = ScoresOrchestration(api_handler, exam)
                    exam_orca.main()
                    fake_running_dt += timedelta(seconds=5)
                    end: datetime = fake_running_dt
                    self.exams_time_metadata[exam.id] = {
                        'start_time': start,
                        'end_time': end,
                        'sub_time_filter': exam_orca.sub_time_filter
                    }
                    fake_running_dt += timedelta(seconds=1)

        self.fake_finished_at: datetime = fake_running_dt
        self.expected_subject: str = (
            'Placement Exams Report - Potions - Success: 4, Failure: 1, New: 2 - Run finished at 2020-06-25 12:00 PM'
        )

    def test_prepare_context(self):
        """
        prepare_context properly uses accumulated time metadata and database records to create a context.
        """
        reporter: Reporter = Reporter(self.potions_report)
        # Check that Reporter is initialized with no data
        self.assertEqual(
            (reporter.total_successes, reporter.total_failures, reporter.total_new, reporter.context),
            (0, 0, 0, dict())
        )

        # I decided to keep Reporter initialization in tests (not setUp), so time metadata is assigned all at once here.
        # This is different from main() in entry.py, where key-value pairs are accumulated.
        reporter.exams_time_metadata = self.exams_time_metadata
        reporter.prepare_context()

        self.assertEqual((reporter.total_successes, reporter.total_failures, reporter.total_new), (4, 1, 2))
        self.assertEqual(sorted(list(reporter.context.keys())), ['exams', 'report', 'support_email'])
        self.assertEqual(reporter.context['report'], {
            'id': 1,
            'name': 'Potions',
            'contact': 'halfbloodprince@hogwarts.edu',
            'summary': {'success_count': 4, 'failure_count': 1, 'new_count': 2}
        })
        self.assertEqual(len(reporter.context['exams']), 2)

        first_exam_dict: dict[str, Any] = reporter.context['exams'][0]
        second_exam_dict: dict[str, Any] = reporter.context['exams'][1]

        keys_list: list[list[str]] = [
            [
                'assignment_id', 'course_id', 'default_time_filter', 'failures', 'id', 'name', 'report', 'sa_code',
                'successes', 'summary', 'time'
            ],
            sorted(list(first_exam_dict.keys())),
            sorted(list(second_exam_dict.keys()))
        ]
        self.assertEqual(keys_list.count(keys_list[0]), 3)

        # Check whether time metadata correctly incorporated
        self.assertEqual(first_exam_dict['time'], self.exams_time_metadata[1])
        self.assertEqual(second_exam_dict['time'], self.exams_time_metadata[2])

        # Check whether QuerySet-derived lists have correct lengths
        self.assertEqual(len(first_exam_dict['successes']), 0)
        self.assertEqual(len(first_exam_dict['failures']), 1)
        self.assertEqual(len(second_exam_dict['successes']), 4)
        self.assertEqual(len(second_exam_dict['failures']), 0)

        # Check roughly that failures and successes are present
        self.assertEqual(
            first_exam_dict['failures'][0],
            {
                'submission_id': 123458,
                'student_uniqname': 'rweasley',
                'score': 150.0,
                'graded_timestamp': datetime(2020, 6, 12, 16, 0, 0, tzinfo=utc)
            }
        )
        val_success_ids: list[int] = sorted(
            [success_dict['submission_id'] for success_dict in second_exam_dict['successes']]
        )
        self.assertEqual(val_success_ids, [123460, 210000, 444444, 444445])

    def test_get_subject(self):
        """
        get_subject properly uses the report instance and count instance variables to return a subject string.
        """
        reporter: Reporter = Reporter(self.potions_report)
        reporter.exams_time_metadata = self.exams_time_metadata
        reporter.prepare_context()

        with patch('pe.reporter.datetime', autospec=True) as mock_datetime:
            mock_datetime.now.return_value = self.fake_finished_at
            subject: str = reporter.get_subject()

        self.assertEqual(subject, self.expected_subject)

    def test_send_email(self):
        """
        send_email properly renders plain text and HTML strings (localizing times) using the context and sends an email.
        """
        # Set up snapshots
        with open(os.path.join(SNAPSHOTS_DIR, 'email_snap.txt'), 'r') as email_snap_plain_file:
            email_snap_plain: str = email_snap_plain_file.read()

        with open(os.path.join(SNAPSHOTS_DIR, 'email_snap.html'), 'r') as email_snap_html_file:
            email_snap_html: str = email_snap_html_file.read()

        reporter: Reporter = Reporter(self.potions_report)
        reporter.exams_time_metadata = self.exams_time_metadata

        # Patch os.environ to override environment variables
        with patch.dict(os.environ, {'SUPPORT_EMAIL': 'admin@hogwarts.edu', 'SMTP_FROM': 'admin@hogwarts.edu'}):
            reporter.prepare_context()
            with patch('pe.reporter.datetime', autospec=True) as mock_datetime:
                mock_datetime.now.return_value = self.fake_finished_at
                reporter.send_email()

        self.assertEqual(len(mail.outbox), 1)
        email: EmailMultiAlternatives = mail.outbox[0]

        self.assertEqual(len(email.alternatives), 1)
        self.assertEqual(email.alternatives[0][1], 'text/html')
        email_html_msg: str = email.alternatives[0][0]

        # Check subject, to, and from
        self.assertEqual(email.subject, self.expected_subject)
        self.assertEqual(email.to, ['halfbloodprince@hogwarts.edu'])
        self.assertEqual(email.from_email, 'admin@hogwarts.edu')

        # Check that body matches plain text snapshot
        self.assertEqual(email.body, email_snap_plain)

        # Check that HTML alternative matches HTML snapshot
        self.assertEqual(email_html_msg, email_snap_html)
