# standard libraries
import logging, os
from datetime import datetime
from typing import Any, Dict, List, Tuple

# third-party libraries
from django.db.models import QuerySet
from django.test import TestCase
from django.utils.timezone import utc
from umich_api.api_utils import ApiUtil

# local libraries
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

    def test_constructor_uses_latest_graded_dt_when_multiple_subs(self):
        """
        Assigns datetime of last graded submission to sub_time_filter when exam has more than one previous submission.
        """
        potions_place_exam = Exam.objects.filter(name='Potions Placement').first()

        some_orca = ScoresOrchestration(self.api_handler, potions_place_exam)

        # Extra second for standard one-second increment
        self.assertEqual(some_orca.sub_time_filter, datetime(2020, 6, 12, 16, 3, 1, tzinfo=utc))

    def test_constructor_uses_default_filter_when_no_subs(self):
        """
        Assigns the exam's default_time_filter value to sub_time_filter when the exam has no previous submissions.
        """
        dada_place_exam = Exam.objects.filter(name='DADA Placement').first()

        some_orca = ScoresOrchestration(self.api_handler, dada_place_exam)
        self.assertEqual(some_orca.sub_time_filter, datetime(2020, 7, 1, 0, 0, 0, tzinfo=utc))

    # def test_constructor_sets_latest_sub_dt_when_exactly_one_sub

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
        place_exam = Exam.objects.filter(name='Potions Placement').first()

        some_orca = ScoresOrchestration(self.api_handler, place_exam)
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

        place_exam = Exam.objects.filter(name='Potions Placement').first()

        some_orca = ScoresOrchestration(self.api_handler, place_exam)
        some_orca.update_sub_records(resp_data)

        self.assertEqual(len(Submission.objects.filter(exam=place_exam, transmitted=True)), 3)

        updated_subs_qs: QuerySet = Submission.objects.filter(exam=place_exam, transmitted_timestamp__gt=current_dt)
        self.assertEqual(len(updated_subs_qs), 1)

        uniqname: str = updated_subs_qs.first().student_uniqname
        self.assertEqual(uniqname, 'rweasley')

        # Ensure un-transmitted submission for another exam with the same uniqname (rweasley) was not updated.
        self.assertFalse(Submission.objects.get(submission_id=210000).transmitted)

    # Mocks needed?
    # def test_get_subs_for_exam(self):

    # Mocks needed?
    # def test_send_scores(self):

    # Mocks needed?
    # def test_main(self):
