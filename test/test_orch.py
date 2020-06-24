# standard libraries
import json, logging, os
from datetime import datetime
from typing import Any, Dict, List, Tuple
from unittest.mock import Mock, patch
from urllib.parse import quote_plus

# third-party libraries
from django.db.models import QuerySet
from django.test import TestCase
from django.utils.timezone import utc
from umich_api.api_utils import ApiUtil

# local libraries
from constants import ISO8601_FORMAT
from pe.models import Exam, Submission
from pe.orchestration import ScoresOrchestration

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGGER = logging.getLogger(__name__)


class ScoresOrchestrationTestCase(TestCase):
    fixtures: List[str] = ['test_01.json', 'test_03.json', 'test_04.json']

    def setUp(self):
        """Set up ApiUtil instance to be used by all ScoresOrchestration tests."""
        # Does this kind of thing need to be wrapped in a try/execpt?
        self.api_handler: ApiUtil = ApiUtil(
            os.getenv('API_DIR_URL', ''),
            os.getenv('API_DIR_CLIENT_ID', ''),
            os.getenv('API_DIR_SECRET', ''),
            os.path.join(ROOT_DIR, 'config', 'apis.json')
        )

        canvas_subs_path: str = os.path.join(ROOT_DIR, 'test', 'api_fixtures', 'canvas_subs.json')
        with open(canvas_subs_path, 'r') as test_canvas_subs_file:
            self.canvas_potions_val_subs = json.loads(test_canvas_subs_file.read())

    def test_constructor_uses_latest_graded_dt_when_subs(self):
        """
        Assigns datetime of last graded submission to sub_time_filter when exam has more than one previous submission.
        """
        potions_place_exam: Exam = Exam.objects.filter(name='Potions Placement').first()

        some_orca: ScoresOrchestration = ScoresOrchestration(self.api_handler, potions_place_exam)

        # Extra second for standard one-second increment
        self.assertEqual(some_orca.sub_time_filter, datetime(2020, 6, 12, 16, 3, 1, tzinfo=utc))

    def test_constructor_uses_default_filter_when_no_subs(self):
        """
        Assigns the exam's default_time_filter value to sub_time_filter when the exam has no previous submissions.
        """
        dada_place_exam: Exam = Exam.objects.filter(name='DADA Placement').first()

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
        """
        get_sub_dicts_for_exam collects one page of submission data and then stops.
        """
        potions_val_exam: Exam = Exam.objects.get(id=2)
        some_orca: ScoresOrchestration = ScoresOrchestration(self.api_handler, potions_val_exam)

        with patch('pe.orchestration.api_call_with_retries') as mock_retry_func:
            mock_retry_func.return_value = Mock(
                ok=True, links={}, text=json.dumps(self.canvas_potions_val_subs[:1])
            )
            sub_dicts = some_orca.get_sub_dicts_for_exam()

        self.assertEqual(mock_retry_func.call_count, 1)
        self.assertTrue(len(sub_dicts), 1)
        self.assertEqual(sub_dicts[0], self.canvas_potions_val_subs[0])

    def test_get_sub_dicts_for_exam_with_multiple_pages(self):
        """
        get_sub_dicts_for_exam collects submission data across two pages.
        """
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

        mocks: List[Mock] = [
            Mock(ok=True, links=first_links, text=json.dumps(self.canvas_potions_val_subs[0:1])),
            Mock(ok=True, links={}, text=json.dumps(self.canvas_potions_val_subs[1:]))
        ]

        with patch('pe.orchestration.api_call_with_retries') as mock_retry_func:
            mock_retry_func.side_effect = mocks
            sub_dicts = some_orca.get_sub_dicts_for_exam(1)

        self.assertTrue(mock_retry_func.call_count, 2)
        self.assertTrue(len(sub_dicts), 2)
        self.assertEqual(sub_dicts, self.canvas_potions_val_subs)

    def test_create_sub_records(self):
        """
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

    def test_update_sub_records_when_all_successful(self):
        """
        update_sub_records updates exam-specific records with transmitted as True and timestamp when all successful.
        """
        current_dt: datetime = datetime.now(tz=utc)

        resp_data: Dict[str, Any] = {
            'putPlcExamScoreResponse': {
                '@schemaLocation': '<The real schema string would go here>',
                'putPlcExamScoreResponse': {
                    'GoodCount': 2,
                    'Success': [
                        {
                            'uniqname': 'rweasley',
                            'placementType': 'PP'
                        },
                        {
                            'uniqname': 'nlongbottom',
                            'placementType': 'PP'
                        }
                    ],
                    'BadCount': 0,
                    'Errors': 'No errors found'
                }
            }
        }
        place_exam: Exam = Exam.objects.filter(name='Potions Placement').first()

        some_orca: ScoresOrchestration = ScoresOrchestration(self.api_handler, place_exam)
        some_orca.update_sub_records(resp_data)

        self.assertEqual(len(Submission.objects.filter(exam=place_exam, transmitted=True)), 4)

        updated_subs_qs: QuerySet = Submission.objects.filter(exam=place_exam, transmitted_timestamp__gt=current_dt)
        self.assertEqual(len(updated_subs_qs), 2)

        uniqnames: List[Tuple[str]] = list(updated_subs_qs.order_by('student_uniqname').values_list('student_uniqname'))
        self.assertEqual(uniqnames, [('nlongbottom',), ('rweasley',)])

        # Ensure un-transmitted submission for another exam with the same uniqname (rweasley) was not updated.
        self.assertFalse(Submission.objects.get(submission_id=210000).transmitted)

    def test_update_sub_records_when_mix_of_success_and_error(self):
        """
        update_sub_records updates exam-specific records with transmitted as True and timestamp only when successful.
        """
        current_dt: datetime = datetime.now(tz=utc)

        resp_data: Dict[str, Any] = {
            'putPlcExamScoreResponse': {
                '@schemaLocation': '<The real schema string would go here>',
                'putPlcExamScoreResponse': {
                    'GoodCount': 1,
                    'Success': {   # Hoping that we can change this format to always use an enclosing array
                        'uniqname': 'rweasley',
                        'placementType': 'PP'
                    },
                    'BadCount': 1,
                    'Errors': {
                        'uniqname': 'nlongbottom',
                        'placementType': 'PP',
                        'reason': 'Some error'
                    }
                }
            }
        }

        place_exam: Exam = Exam.objects.filter(name='Potions Placement').first()

        some_orca: ScoresOrchestration = ScoresOrchestration(self.api_handler, place_exam)
        some_orca.update_sub_records(resp_data)

        self.assertEqual(len(Submission.objects.filter(exam=place_exam, transmitted=True)), 3)

        updated_subs_qs: QuerySet = Submission.objects.filter(exam=place_exam, transmitted_timestamp__gt=current_dt)
        self.assertEqual(len(updated_subs_qs), 1)

        uniqname: str = updated_subs_qs.first().student_uniqname
        self.assertEqual(uniqname, 'rweasley')

        # Ensure un-transmitted submission for another exam with the same uniqname (rweasley) was not updated.
        self.assertFalse(Submission.objects.get(submission_id=210000).transmitted)

    # def test_send_scores_when_successful(self):

    # def test_send_scores_when_not_successful(self):

    # Mocks needed?
    # def test_main(self):
