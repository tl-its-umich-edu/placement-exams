# standard libraries
import json, logging, os
from typing import Any, Dict

# third-party libraries
from django.test import TestCase
from jsonschema import validate

# Local libraries
from configure import FIXTURES_SCHEMA
from db.models import Report, Exam
from db.utils import load_fixtures


LOGGER = logging.getLogger(__name__)

TEST_FIXTURES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')

EXAM_FIELDS = ('name', 'report_id', 'sa_code', 'course_id', 'assignment_id')


def prepare_fixture_data(file_name: str) -> Dict[str, Any]:
    '''Opens, parses, and validates a JSON fixture file for testng purposes'''

    with open(os.path.join(TEST_FIXTURES_PATH, file_name)) as fixture_file:
        fixtures = json.loads(fixture_file.read())
    
    try:
        validate(instance=fixtures, schema=FIXTURES_SCHEMA)
        LOGGER.debug(f'Test fixture JSON in {file_name} is valid')
    except Exception as e:
        LOGGER.error(e)
        LOGGER.error(f'Test fixture JSON in {file_name} is invalid')

    return fixtures


class LoadFixturesTestCase(TestCase):

    def test_fixtures_load_when_db_is_empty(self):
        '''
        Loading fixtures results in new model instances when the database is empty.
        This tests the creation of Report and Exam models using load_fixtures.
        '''

        fake_fixtures = prepare_fixture_data('fake_fixtures.json')
        load_fixtures(fake_fixtures)

        # Test Potions report loaded
        report_queryset = Report.objects.filter(id=1)
        self.assertTrue(report_queryset.exists())
        if report_queryset.exists():
            self.assertEqual(
                report_queryset.values()[0],
                {
                    "id": 1,
                    "name": "Potions", 
                    "contact": "halfbloodprince@hogwarts.edu"
                }
            )

        # Test exams loaded
        exams_queryset = Exam.objects.all()
        self.assertTrue(exams_queryset.exists())
        self.assertTrue(len(exams_queryset), 2)
        if exams_queryset.exists() and len(exams_queryset) == 2:

            placement_queryset = exams_queryset.filter(name='Potions Placement')
            self.assertTrue(placement_queryset.exists())
            if placement_queryset.exists():
                self.assertEqual(
                    placement_queryset.values(*EXAM_FIELDS)[0],
                    {
                        "name": "Potions Placement",
                        "report_id": 1,
                        "sa_code": "PP",
                        "course_id": 888888,
                        "assignment_id": 111111
                    }
                )

            validation_queryset = exams_queryset.filter(name='Potions Validation')
            self.assertTrue(validation_queryset.exists())
            if validation_queryset.exists():
                self.assertEqual(
                    validation_queryset.values(*EXAM_FIELDS)[0],
                    {
                        "name": "Potions Validation",
                        "report_id": 1,
                        "sa_code": "PV",
                        "course_id": 888888,
                        "assignment_id": 111112
                    }
                )

    def test_fixtures_load_updates_when_data_in_db(self):
        '''
        Loading fixtures results in updated model instances.
        The assertions test whether all change-able properties of Report (everything but id) and Exam (everything but sa_code)
        are properly updated. This test assumes the prior test case succeeded.
        '''

        # Load previous test's fixtures
        fake_fixtures = prepare_fixture_data('fake_fixtures.json')
        load_fixtures(fake_fixtures)

        # Load current test's fixtures
        fake_fixtures_updated = prepare_fixture_data('fake_fixtures_updated.json')
        load_fixtures(fake_fixtures_updated)

        # Test Potions report name and contact changed
        potions_report = Report.objects.get(id=1)
        self.assertEqual(potions_report.name, 'Placement Potions')
        self.assertEqual(potions_report.contact, 'hslughorn@hogwarts.edu')

        # Test Placement Potions exam name and course_id changed
        placement_exam = Exam.objects.get(sa_code='PP')
        self.assertEqual(placement_exam.name, 'Potions Placement Advanced')
        self.assertEqual(placement_exam.course_id, 888889)

        # Test Potions Validation report and assignment_id changed
        validation_exam = Exam.objects.get(name='Potions Validation')
        self.assertTrue(validation_exam.assignment_id, 111113)

        new_report_queryset = Report.objects.filter(id=2)
        self.assertTrue(new_report_queryset.exists())
        if new_report_queryset.exists():
            self.assertEqual(validation_exam.report, new_report_queryset[0])

    def test_fixtures_load_adds_data_when_data_in_db(self):
        '''
        Loading brand new fixtures results in new objects while previous ones remain in the database.
        This test assumes the previous test case succeeded.
        '''

        # Load previous test's fixtures
        fake_fixtures = prepare_fixture_data('fake_fixtures_updated.json')
        load_fixtures(fake_fixtures)

        fake_new_fixtures = prepare_fixture_data('fake_new_fixtures.json')

        load_fixtures(fake_new_fixtures)

        # Test previous Potions report remains and new DADA report was added
        report_queryset = Report.objects.all()
        self.assertTrue(len(report_queryset), 2)
        self.assertTrue(report_queryset.filter(id=1).exists())

        dada_queryset = report_queryset.filter(id=2)
        self.assertTrue(dada_queryset.exists())
        if dada_queryset.exists():
            self.assertEqual(
                dada_queryset.values()[0],
                {
                    "id": 2,
                    "name": "Defense Against the Dark Arts",
                    "contact": "rlupin@hogwarts.edu"
                }
            )

        # Test previous exams remain and new DADA Placement exam added
        exams_queryset = Exam.objects.all()
        self.assertTrue(len(exams_queryset), 3)
        previous_queryset = exams_queryset.filter(name__in=['Potions Placement Advancecd', 'Potions Validation'])
        self.assertTrue(len(previous_queryset), 2)

        data_exam_queryset = exams_queryset.filter(name='DADA Placement')
        self.assertTrue(data_exam_queryset.exists())
        if data_exam_queryset.exists():
            self.assertEqual(
                data_exam_queryset.values(*EXAM_FIELDS)[0],
                {
                    "sa_code": "DDP",
                    "name": "DADA Placement",
                    "report_id": 2,
                    "course_id": 999999,
                    "assignment_id": 222222
                }
            )
