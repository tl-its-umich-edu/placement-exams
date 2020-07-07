# standard libraries
import json, logging, os
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

# third-party libraries
from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.template import Context, Template
from django.test import TestCase
from django.utils.timezone import utc
from requests import Response
from umich_api.api_utils import ApiUtil

# local libraries
from constants import API_FIXTURES_DIR, ROOT_DIR
from pe.models import Report
from pe.orchestration import ScoresOrchestration
from pe.reporter import Reporter


LOGGER = logging.getLogger(__name__)


class ReporterSuccessTestCase(TestCase):
    fixtures: List[str] = ['test_01.json', 'test_04.json']

    def setUp(self):
        """
        Intializes ApiUtil instance, fixtures, and report, and runs orchestrations for report, gathering time metadata.
        """
        api_handler: ApiUtil = ApiUtil(
            os.getenv('API_DIR_URL', ''),
            os.getenv('API_DIR_CLIENT_ID', ''),
            os.getenv('API_DIR_SECRET', ''),
            os.path.join(ROOT_DIR, 'config', 'apis.json')
        )

        with open(os.path.join(API_FIXTURES_DIR, 'canvas_subs.json'), 'r') as test_canvas_subs_file:
            self.canvas_potions_val_subs: List[Dict[str, Any]] = json.loads(test_canvas_subs_file.read())

        with open(os.path.join(API_FIXTURES_DIR, 'mpathways_resp_data.json'), 'r') as mpathways_resp_data_file:
            self.mpathways_resp_data: List[Dict[str, Any]] = json.loads(mpathways_resp_data_file.read())

        self.potions_report = Report.objects.get(id=1)

        with patch('pe.orchestration.api_call_with_retries', autospec=True) as mock_get:
            with patch.object(ApiUtil, 'api_call', autospec=True) as mock_send:
                mock_get.side_effect = [
                    # Potions Placement - no more new submissions
                    MagicMock(spec=Response, status_code=200, text=json.dumps([])),
                    # Potions Validation - two more new submissions
                    MagicMock(spec=Response, status_code=200, text=json.dumps(self.canvas_potions_val_subs))
                ]
                mock_send.side_effect = [
                    # Potions Placement - Only rweasley sub from test_04.json, fails to send
                    MagicMock(spec=Response, status_code=200, text=json.dumps(self.mpathways_resp_data[5])),
                    # Potions Validation - Four subs, two from canvas_subs.json, two from test_04.json, all send
                    MagicMock(spec=Response, status_code=200, text=json.dumps(self.mpathways_resp_data[2]))
                ]

                self.exams_time_metadata = {}
                for exam in self.potions_report.exams.all():
                    start: datetime = datetime.now(tz=utc)
                    exam_orca = ScoresOrchestration(api_handler, exam)
                    exam_orca.main()
                    end: datetime = datetime.now(tz=utc)
                    self.exams_time_metadata[exam.id] = {
                        'start_time': start,
                        'end_time': end,
                        'datetime_filter': exam_orca.sub_time_filter
                    }

        self.expected_subject: str = (
            'Placement Exams Report - Potions - Success: 4, Failure: 1, New: 2 - Potions Placement, Potions Validation'
        )

    def test_prepare_context(self):
        """
        prepare_context properly uses accumulated time metadata and database records to create a context.
        """
        reporter = Reporter(self.potions_report)
        # Initialized with no data
        self.assertEqual(
            (reporter.total_successes, reporter.total_failures, reporter.total_new, reporter.context),
            (0, 0, 0, {})
        )
        
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

        first_exam_dict = reporter.context['exams'][0]
        second_exam_dict = reporter.context['exams'][1]

        # Maybe replace with JSON Schema?
        keys_list: List[List[str]] = [
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

        self.assertEqual(len(first_exam_dict['successes']), 0)
        self.assertEqual(len(first_exam_dict['failures']), 1)
        self.assertEqual(len(second_exam_dict['successes']), 4)
        self.assertEqual(len(second_exam_dict['failures']), 0)

        self.assertEqual(
            first_exam_dict['failures'][0],
            {
                'submission_id': 123458,
                'student_uniqname': 'rweasley',
                'score': 150.0,
                'submitted_timestamp': datetime(2020, 6, 12, 12, 50, 7, tzinfo=utc)
            }
        )
        val_success_ids: List[int] = sorted(
            [success_dict['submission_id'] for success_dict in second_exam_dict['successes']]
        )
        self.assertEqual(val_success_ids, [123460, 210000, 444444, 444445])

    def test_get_subject(self):
        """
        get_subject properly uses the report instance and count instance variables to return a subject string.
        """
        reporter = Reporter(self.potions_report)
        reporter.exams_time_metadata = self.exams_time_metadata
        reporter.prepare_context()

        self.assertEqual(reporter.get_subject(), self.expected_subject)

    def test_send_email(self):
        """
        send_email properly renders plain text and HTML strings (localizing times) using the context and sends an email.
        """
        reporter = Reporter(self.potions_report)
        reporter.exams_time_metadata = self.exams_time_metadata
        reporter.prepare_context()
        reporter.send_email()

        self.assertEqual(len(mail.outbox), 1)
        email: EmailMultiAlternatives = mail.outbox[0]
        self.assertEqual(email.subject, self.expected_subject)
        self.assertEqual(email.to, ['halfbloodprince@hogwarts.edu'])

        self.assertEqual(len(email.alternatives), 1)
        self.assertEqual(email.alternatives[0][1], 'text/html')
        email_html_msg: str = email.alternatives[0][0]

        # Check that exam summary block/table is properly generated.
        # This needs to be generated programmatically since the times are created at runtime.
        process_time_template: Template = Template('Process Start: {{ start_time }}\nProcess End: {{ end_time }}\n')
        process_time_context: Context = Context(self.exams_time_metadata[1])
        process_time_block: str = process_time_template.render(process_time_context)
        placement_summary_block: str = (
            'Exam: Potions Placement\nCanvas Course ID: 888888\nCanvas Assignment ID: 111111\n' +
            process_time_block +
            'Time used for filtering Canvas submissions: June 12, 2020 12:00:01 p.m.\n' +
            'New submissions count: 0'
        )
        self.assertTrue(placement_summary_block in email.body)

        # HTML equivalent?

        # Check that report indicates no scores were sent successfuly
        no_successes_msg: str = 'The application did not send any scores for the Potions Placement exam.'
        self.assertTrue(no_successes_msg in email.body)
        self.assertTrue(no_successes_msg in email_html_msg)

        # Check that report indicates the application did not fail to send any scores
        no_failures_msg: str = 'The application did not fail to send any scores for the Potions Validation exam.'
        self.assertTrue(no_failures_msg in email.body)
        self.assertTrue(no_successes_msg in email_html_msg)

        headers: str = 'Canvas ID - Student Uniqname - Score - Submitted At'

        # Check that failed score sending is reported for Potions Placement
        failed_sub_block: str = '\n\n'.join(
            ['Failures: Scores not transmitted', headers, '123458 - rweasley - 150.0 - June 12, 2020 8:50:07 a.m.']
        )
        self.assertTrue(failed_sub_block in email.body)

        # HTML equivalent?

        # Check that successfully sent scores are reported for Potions Validation
        success_sub_block: str = '\n\n'.join(
            [
                'Successes: Scores transmitted', headers,
                '123460 - nlongbottom - 300.0 - June 12, 2020 9:05:01 a.m.',
                '210000 - rweasley - 150.0 - June 13, 2020 6:05:00 a.m.',
                '444444 - hpotter - 125.0 - June 19, 2020 1:45:33 p.m.',
                '444445 - cchang - 200.0 - June 20, 2020 6:35:01 a.m.'
            ]
        )
        self.assertTrue(success_sub_block in email.body)

        # HTML equivalent?
