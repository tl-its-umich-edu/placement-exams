# standard libraries
import json, logging, os
from datetime import datetime
from typing import Any, Dict, List, Tuple
from unittest.mock import MagicMock, patch
from urllib.parse import quote_plus

# third-party libraries
from django.db.models import QuerySet
from django.test import TestCase
from django.utils.timezone import utc
from requests import Response
from umich_api.api_utils import ApiUtil

# local libraries
from constants import ISO8601_FORMAT, MPATHWAYS_SCOPE
from pe.models import Exam, Submission
from pe.orchestration import ScoresOrchestration


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_FIXTURES_PATH = os.path.join(ROOT_DIR, 'test', 'api_fixtures')
LOGGER = logging.getLogger(__name__)


class ScoresOrchestrationTestCase(TestCase):
    fixtures: List[str] = ['test_01.json', 'test_03.json', 'test_04.json']

    def setUp(self):
        """Sets up ApiUtil instance and custom fixtures to be used by ScoresOrchestration tests."""
        self.api_handler: ApiUtil = ApiUtil(
            os.getenv('API_DIR_URL', ''),
            os.getenv('API_DIR_CLIENT_ID', ''),
            os.getenv('API_DIR_SECRET', ''),
            os.path.join(ROOT_DIR, 'config', 'apis.json')
        )

        with open(os.path.join(API_FIXTURES_PATH, 'canvas_subs.json'), 'r') as test_canvas_subs_file:
            self.canvas_potions_val_subs: List[Dict[str, Any]] = json.loads(test_canvas_subs_file.read())

        with open(os.path.join(API_FIXTURES_PATH, 'mpathways_resp_data.json'), 'r') as mpathways_resp_data_file:
            self.mpathways_resp_data: List[Dict[str, Any]] = json.loads(mpathways_resp_data_file.read())

    def test_constructor_uses_latest_graded_dt_when_subs(self):
        """
        Constructor assigns last submission graded datetime to sub_time_filter when exam has previous submissions.
        """
        potions_place_exam: Exam = Exam.objects.get(id=1)

        some_orca: ScoresOrchestration = ScoresOrchestration(self.api_handler, potions_place_exam)

        # Extra second for standard one-second increment
        self.assertEqual(some_orca.sub_time_filter, datetime(2020, 6, 12, 16, 0, 1, tzinfo=utc))

    def test_constructor_uses_default_filter_when_no_subs(self):
        """
        Constructor assigns the exam's default_time_filter to sub_time_filter when the exam has no previous submissions.
        """
        dada_place_exam: Exam = Exam.objects.get(id=3)

        some_orca = ScoresOrchestration(self.api_handler, dada_place_exam)
        self.assertEqual(some_orca.sub_time_filter, datetime(2020, 7, 1, 0, 0, 0, tzinfo=utc))

    def test_get_sub_dicts_for_exam_with_null_response(self):
        """
        get_sub_dicts_for_exam stops collecting data and paginating if api_call_with_retries returns None.
        """
        potions_val_exam: Exam = Exam.objects.get(id=2)
        some_orca: ScoresOrchestration = ScoresOrchestration(self.api_handler, potions_val_exam)

        with patch('pe.orchestration.api_call_with_retries') as mock_retry_func:
            mock_retry_func.return_value = None
            sub_dicts = some_orca.get_sub_dicts_for_exam()

        self.assertEqual(mock_retry_func.call_count, 1)
        self.assertEqual(len(sub_dicts), 0)

    def test_get_sub_dicts_for_exam_with_one_page(self):
        """get_sub_dicts_for_exam collects one page of submission data and then stops."""
        potions_val_exam: Exam = Exam.objects.get(id=2)
        some_orca: ScoresOrchestration = ScoresOrchestration(self.api_handler, potions_val_exam)

        with patch('pe.orchestration.api_call_with_retries', autospec=True) as mock_retry_func:
            mock_retry_func.return_value = MagicMock(
                spec=Response, ok=True, links={}, text=json.dumps(self.canvas_potions_val_subs[:1])
            )
            sub_dicts = some_orca.get_sub_dicts_for_exam()

        self.assertEqual(mock_retry_func.call_count, 1)
        self.assertEqual(len(sub_dicts), 1)
        self.assertEqual(sub_dicts[0], self.canvas_potions_val_subs[0])

    def test_get_sub_dicts_for_exam_with_multiple_pages(self):
        """get_sub_dicts_for_exam collects submission data across two pages."""
        potions_val_exam = Exam.objects.get(id=2)
        some_orca: ScoresOrchestration = ScoresOrchestration(self.api_handler, potions_val_exam)

        first_links: Dict[str, Any] = {
            # This is probably more elaborate than it needs to be, but this way the DEBUG log message of
            # page_info will show parameters that make sense in this context.
            'next': {
                'url': (
                    f'https://apigw-tst.it.umich.edu/um/aa/CanvasReadOnly/courses/{some_orca.exam.course_id}' +
                    f'/students/submissions?assignment_ids={some_orca.exam.assignment_id}' +
                    f'&graded_since={quote_plus(some_orca.sub_time_filter.strftime(ISO8601_FORMAT))}&include=user' +
                    '&student_ids=all&page=bookmark:SomeBookmark&per_page=1'
                ),
                'rel': 'next'
            }
        }

        mocks: List[MagicMock] = [
            MagicMock(spec=Response, ok=True, links=first_links, text=json.dumps(self.canvas_potions_val_subs[0:1])),
            MagicMock(spec=Response, ok=True, links={}, text=json.dumps(self.canvas_potions_val_subs[1:]))
        ]

        with patch('pe.orchestration.api_call_with_retries', autospec=True) as mock_retry_func:
            mock_retry_func.side_effect = mocks
            sub_dicts = some_orca.get_sub_dicts_for_exam(1)

        self.assertEqual(mock_retry_func.call_count, 2)
        self.assertEqual(len(sub_dicts), 2)
        self.assertEqual(sub_dicts, self.canvas_potions_val_subs)

    def test_create_sub_records(self):
        """
        create_sub_records parses Canvas submission dictionaries and creates records in the database.
        """
        potions_val_exam = Exam.objects.get(id=2)
        some_orca: ScoresOrchestration = ScoresOrchestration(self.api_handler, potions_val_exam)
        some_orca.create_sub_records(self.canvas_potions_val_subs)

        new_potions_val_sub_qs: QuerySet = some_orca.exam.submissions.filter(submission_id__in=[444444, 444445])
        self.assertEqual(len(new_potions_val_sub_qs), 2)

        self.assertEqual(len(new_potions_val_sub_qs.filter(transmitted=False, transmitted_timestamp=None)), 2)

        sub_dicts: List[Dict[str, Any]] = new_potions_val_sub_qs.order_by('student_uniqname').values(
            'submission_id', 'student_uniqname', 'score', 'submitted_timestamp', 'graded_timestamp'
        )
        self.assertEqual(
            sub_dicts[0],
            {
                'submission_id': 444445,
                'student_uniqname': 'cchang',
                'score': 200.0,
                'submitted_timestamp': datetime(2020, 6, 20, 10, 35, 1, tzinfo=utc),
                'graded_timestamp': datetime(2020, 6, 20, 10, 45, 0, tzinfo=utc)
            }
        )
        self.assertEqual(
            sub_dicts[1],
            {
                'submission_id': 444444,
                'student_uniqname': 'hpotter',
                'score': 125.0,
                'submitted_timestamp': datetime(2020, 6, 19, 17, 45, 33, tzinfo=utc),
                'graded_timestamp': datetime(2020, 6, 19, 17, 45, 33, tzinfo=utc)
            }
        )

    def test_send_scores_when_successful(self):
        """send_scores generates proper request and returns resp_data when successful."""
        resp_data: Dict[str, Any] = self.mpathways_resp_data[0]
        potions_val_exam: Exam = Exam.objects.get(id=2)
        some_orca: ScoresOrchestration = ScoresOrchestration(self.api_handler, potions_val_exam)

        val_subs: List[Submission] = list(some_orca.exam.submissions.filter(transmitted=False))
        scores_to_send: List[Dict[str, str]] = [sub.prepare_score() for sub in val_subs]

        with patch.object(ApiUtil, 'api_call', autospec=True) as mock_api_call:
            mock_api_call.return_value = MagicMock(spec=Response, status_code=200, text=json.dumps(resp_data))

            result = some_orca.send_scores(scores_to_send)

        self.assertEqual(mock_api_call.call_count, 1)
        mock_api_call.assert_called_with(
            self.api_handler,
            'aa/SpanishPlacementScores/Scores',
            MPATHWAYS_SCOPE,
            'PUT',
            payload=json.dumps({'putPlcExamScore': {'Student': scores_to_send}}),
            api_specific_headers=[{'Content-Type': 'application/json'}]
        )
        self.assertEqual(result, resp_data)

    def test_send_scores_when_not_successful(self):
        """send_scores generates proper request and returns None when not successful."""
        potions_val_exam: Exam = Exam.objects.get(id=2)
        some_orca: ScoresOrchestration = ScoresOrchestration(self.api_handler, potions_val_exam)

        val_subs: List[Submission] = list(some_orca.exam.submissions.filter(transmitted=False))

        self.api_handler.api_call = MagicMock(
            spec=ApiUtil.api_call,
            return_value=MagicMock(spec=Response, status_code=404, text=json.dumps({}))
        )
        scores_to_send: List[Dict[str, str]] = [sub.prepare_score() for sub in val_subs]
        result = some_orca.send_scores(scores_to_send)

        self.api_handler.api_call.assert_called_with(
            'aa/SpanishPlacementScores/Scores',
            MPATHWAYS_SCOPE,
            'PUT',
            payload=json.dumps({'putPlcExamScore': {'Student': scores_to_send}}),
            api_specific_headers=[{'Content-Type': 'application/json'}]
        )
        self.assertEqual(self.api_handler.api_call.call_count, 1)
        self.assertEqual(result, None)

    def test_update_sub_records_when_all_successful(self):
        """
        update_sub_records updates exam-specific records with transmitted as True and timestamp when all successful.
        """
        current_dt: datetime = datetime.now(tz=utc)

        resp_data: Dict[str, Any] = self.mpathways_resp_data[0]
        potions_val_exam: Exam = Exam.objects.get(id=2)
        some_orca: ScoresOrchestration = ScoresOrchestration(self.api_handler, potions_val_exam)

        some_orca.update_sub_records(resp_data)

        self.assertEqual(len(Submission.objects.filter(exam=potions_val_exam, transmitted=True)), 2)
        updated_subs_qs: QuerySet = Submission.objects.filter(
            exam=potions_val_exam, transmitted_timestamp__gt=current_dt
        )
        self.assertEqual(len(updated_subs_qs), 2)
        uniqnames: List[Tuple[str]] = list(updated_subs_qs.order_by('student_uniqname').values_list('student_uniqname'))
        self.assertEqual(uniqnames, [('nlongbottom',), ('rweasley',)])

        # Ensure un-transmitted submission for another exam (Potions Placement)
        # with the same uniqname (rweasley) was not updated.
        self.assertFalse(Submission.objects.get(submission_id=123458).transmitted)

    def test_update_sub_records_when_mix_of_success_and_error(self):
        """
        update_sub_records updates exam-specific records with transmitted as True and timestamp only when successful.
        """
        current_dt: datetime = datetime.now(tz=utc)

        resp_data: Dict[str, Any] = self.mpathways_resp_data[1]
        potions_val_exam: Exam = Exam.objects.get(id=2)
        some_orca: ScoresOrchestration = ScoresOrchestration(self.api_handler, potions_val_exam)

        some_orca.update_sub_records(resp_data)

        self.assertEqual(len(Submission.objects.filter(exam=potions_val_exam, transmitted=True)), 1)
        updated_subs_qs: QuerySet = Submission.objects.filter(
            exam=potions_val_exam, transmitted_timestamp__gt=current_dt
        )
        self.assertEqual(len(updated_subs_qs), 1)
        uniqname: str = updated_subs_qs.first().student_uniqname
        self.assertEqual(uniqname, 'rweasley')

        # Ensure un-transmitted submission for another exam (Potions Placement)
        # with the same uniqname (rweasley) was not updated.
        self.assertFalse(Submission.objects.get(submission_id=123458).transmitted)

    def test_main(self):
        """main process method handles both previously un-transmitted and new submissions."""
        potions_val_exam: Exam = Exam.objects.get(id=2)
        some_orca: ScoresOrchestration = ScoresOrchestration(self.api_handler, potions_val_exam)

        # Expected scores from to-be-fetched Canvas submissions (really, canvas_subs.json)
        scores: List[Dict[str, str]] = [
            {
                'ID': 'hpotter',
                'Form': 'PV',
                'GradePoints': '125.0'
            },
            {
                'ID': 'cchang',
                'Form': 'PV',
                'GradePoints': '200.0'
            }
        ]
        # Un-transmitted scores from previous runs (really, test_04.json)
        scores = [sub.prepare_score() for sub in some_orca.exam.submissions.all()] + scores

        with patch.object(ScoresOrchestration, 'get_sub_dicts_for_exam', autospec=True) as mock_get:
            with patch.object(ScoresOrchestration, 'send_scores', autospec=True) as mock_send:
                mock_get.return_value = self.canvas_potions_val_subs
                mock_send.return_value = self.mpathways_resp_data[2]

                some_orca.main()

        self.assertEqual(mock_get.call_count, 1)
        self.assertEqual(mock_send.call_count, 1)
        mock_send.assert_called_once_with(self=some_orca, scores_to_send=scores)

        potions_val_sub_qs: QuerySet = some_orca.exam.submissions.filter(transmitted=True)
        potions_val_subs: List[Submission] = list(potions_val_sub_qs.order_by('student_uniqname').all())
        self.assertEqual(len(potions_val_subs), 4)
        self.assertEqual(
            [sub.student_uniqname for sub in potions_val_subs],
            ['cchang', 'hpotter', 'nlongbottom', 'rweasley']
        )
        brand_new_subs: List[Submission] = list(
            potions_val_sub_qs.filter(graded_timestamp__gte=some_orca.sub_time_filter).order_by('student_uniqname')
        )
        self.assertEqual(len(brand_new_subs), 2)
        self.assertEqual([sub.student_uniqname for sub in brand_new_subs], ['cchang', 'hpotter'])
