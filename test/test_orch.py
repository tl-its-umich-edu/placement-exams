# standard libraries
import logging, os
from datetime import datetime
from typing import List

# third-party libraries
from django.test import TestCase
from django.utils.timezone import utc
from umich_api.api_utils import ApiUtil

# local libraries
from pe.models import Exam   # , Submission
from pe.orchestration import ScoresOrchestration

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGGER = logging.getLogger(__name__)


class OrchestrationTestCase(TestCase):
    fixtures: List[str] = ['test_01.json', 'test_04.json']

    def setUp(self):

        # Does this kind of thing need to be wrapped in a try/execpt?
        self.api_handler: ApiUtil = ApiUtil(
            os.getenv('API_DIR_URL', ''),
            os.getenv('API_DIR_CLIENT_ID', ''),
            os.getenv('API_DIR_SECRET', ''),
            os.path.join(ROOT_DIR, 'config', 'apis.json')
        )

    def test_constructor_uses_latest_graded_dt_when_multiple_subs(self):
        """
        Correctly assigns datetime of last graded submission to Orchestration.filter when
        an exam has more than one previous submission
        """

        place_exam = Exam.objects.filter(name='Potions Placement').first()

        some_orca = ScoresOrchestration(self.api_handler, place_exam)

        # Extra second for standard one-second increment
        self.assertEqual(some_orca.sub_time_filter, datetime(2020, 6, 12, 9, 35, 1, tzinfo=utc))

    def test_constructor_uses_default_filter_when_no_subs(self):
        """
        Correctly assigns the exam's default_time_filter value to Orchestration.filter when the
        exam has no previous submissions
        """

        val_exam = Exam.objects.filter(name='Potions Validation').first()

        some_orca = ScoresOrchestration(self.api_handler, val_exam)
        self.assertEqual(some_orca.sub_time_filter, datetime(2020, 5, 1, 0, 0, 0, tzinfo=utc))

    # def test_constructor_sets_latest_sub_dt_when_exactly_one_sub

    # def test_update_sub_records(self):

    # Mocks needed?
    # def test_get_subs_for_exam(self):

    # Mocks needed?
    # def test_send_scores(self):

    # Mocks needed?
    # def test_main(self):
