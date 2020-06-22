# standard libraries
import logging
from datetime import datetime
from typing import List, Tuple

# third-party libraries
from django.core.management import call_command
from django.test import TestCase
from django.utils.timezone import utc


# Local libraries
from pe.models import Report, Exam, Submission


LOGGER = logging.getLogger(__name__)

EXAM_FIELDS: Tuple[str, ...] = ('name', 'report_id', 'sa_code', 'course_id', 'assignment_id', 'default_time_filter')


class LoadFixturesTestCase(TestCase):

    def test_fixtures_load_when_db_is_empty(self):
        """
        Loading fixtures results in new model instances when the database is empty.
        This tests the creation of Report and Exam models using the loaddata command.
        """

        call_command('loaddata', 'test_01.json')

        # Test Potions report loaded
        report_queryset = Report.objects.filter(id=1)
        self.assertTrue(report_queryset.exists())
        if not report_queryset.exists():
            return None

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
        if not exams_queryset.exists() and len(exams_queryset) != 2:
            return None

        placement_queryset = exams_queryset.filter(name='Potions Placement')
        self.assertTrue(placement_queryset.exists())
        if not placement_queryset.exists():
            return None

        self.assertEqual(
            placement_queryset.values(*EXAM_FIELDS)[0],
            {
                "name": "Potions Placement",
                "report_id": 1,
                "sa_code": "PP",
                "course_id": 888888,
                "assignment_id": 111111,
                "default_time_filter": datetime(2020, 6, 1, 0, 0, 0, tzinfo=utc)
            }
        )

        validation_queryset = exams_queryset.filter(name='Potions Validation')
        self.assertTrue(validation_queryset.exists())
        if not validation_queryset.exists():
            return None

        self.assertEqual(
            validation_queryset.values(*EXAM_FIELDS)[0],
            {
                "name": "Potions Validation",
                "report_id": 1,
                "sa_code": "PV",
                "course_id": 888888,
                "assignment_id": 111112,
                "default_time_filter": datetime(2020, 5, 1, 0, 0, 0, tzinfo=utc)
            }
        )

    def test_fixtures_load_updates_when_data_in_db(self):
        """
        Loading fixtures results in updated model instances.
        The assertions test whether all change-able properties of Report (everything but id) and
        Exam (everything but sa_code) are properly updated. This test assumes the prior test case succeeded.
        """

        # Load previous test's fixtures
        call_command('loaddata', 'test_01.json')

        call_command('loaddata', 'test_02.json')

        # Test Potions report name and contact changed
        potions_report = Report.objects.get(id=1)
        self.assertEqual(potions_report.name, 'Placement Potions')
        self.assertEqual(potions_report.contact, 'hslughorn@hogwarts.edu')

        # Test Placement Potions exam name, course_id, and default_time_filter changed
        placement_exam = Exam.objects.get(sa_code='PP')
        self.assertEqual(placement_exam.name, 'Potions Placement Advanced')
        self.assertEqual(placement_exam.course_id, 888889)
        self.assertEqual(placement_exam.default_time_filter, datetime(2020, 6, 2, 12, 0, 0, tzinfo=utc))

        # Test Potions Validation report and assignment_id changed
        validation_exam = Exam.objects.get(name='Potions Validation')
        self.assertTrue(validation_exam.assignment_id, 111113)

        new_report_queryset = Report.objects.filter(id=2)
        self.assertTrue(new_report_queryset.exists())
        if not new_report_queryset.exists():
            return None

        self.assertEqual(validation_exam.report, new_report_queryset[0])

    def test_fixtures_load_adds_data_when_data_in_db(self):
        """
        Loading brand new fixtures results in new objects while previous ones remain in the database.
        This test assumes the previous test case succeeded.
        """

        # Load previous test's fixtures
        call_command('loaddata', 'test_02.json')

        call_command('loaddata', 'test_03.json')

        # Test previous Potions report remains and new DADA report was added
        report_queryset = Report.objects.all()
        self.assertTrue(len(report_queryset), 2)
        self.assertTrue(report_queryset.filter(id=1).exists())

        dada_queryset = report_queryset.filter(id=3)
        self.assertTrue(dada_queryset.exists())
        if not dada_queryset.exists():
            return None

        self.assertEqual(
            dada_queryset.values()[0],
            {
                "id": 3,
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
        if not data_exam_queryset.exists():
            return None

        self.assertEqual(
            data_exam_queryset.values(*EXAM_FIELDS)[0],
            {
                "sa_code": "DDP",
                "name": "DADA Placement",
                "report_id": 3,
                "course_id": 999999,
                "assignment_id": 222222,
                "default_time_filter": datetime(2020, 7, 1, 0, 0, 0, tzinfo=utc)
            }
        )

    def test_fixtures_load_maintains_submission_link(self):
        """
        Loading submission and updating related exam results in maintained relationship.
        This test assumes the first two test cases succeeded.
        """

        # Load first test's fixtures
        call_command('loaddata', 'test_01.json')

        # Load submission fixture
        call_command('loaddata', 'test_04.json')

        # Test submission loaded correctly
        submission_queryset = Submission.objects.all()
        self.assertTrue(submission_queryset.exists())
        if not submission_queryset.exists():
            return None

        submission_dict = submission_queryset.filter(submission_id=123456).values(
            'submission_id', 'exam_id', 'student_uniqname', 'submitted_timestamp', 'score',
            'transmitted', 'transmitted_timestamp'
        )[0]
        self.assertEqual(
            submission_dict,
            {
                "submission_id": 123456,
                "exam_id": 1,
                "student_uniqname": "hpotter",
                "submitted_timestamp": datetime(2020, 6, 12, 8, 15, 30, tzinfo=utc),
                "score": 100.0,
                "transmitted": True,
                "transmitted_timestamp": datetime(2020, 6, 12, 12, 0, 30, tzinfo=utc)
            }
        )

        # Load second test's fixtures updating reports and exams
        call_command('loaddata', 'test_02.json')

        submission_queryset = Submission.objects.all()
        self.assertTrue(submission_queryset.exists())
        if not submission_queryset.exists():
            return None

        submission = submission_queryset.filter(submission_id=123456).first()
        self.assertEqual(submission.exam.sa_code, 'PP')
        self.assertEqual(submission.exam.name, 'Potions Placement Advanced')


class StringMethodsTestCase(TestCase):
    fixtures: List[str] = ['test_01.json', 'test_04.json']

    def test_report_string_method(self):
        """Report string method should present all variables in the correct format"""

        potions_report = Report.objects.get(id=1)
        self.assertEqual(potions_report.__str__(), '(id=1, name=Potions, contact=halfbloodprince@hogwarts.edu)')

    def test_exam_string_method(self):
        """
        Exam string method should present all variables, and nested Report object, in the correct format.
        """

        potions_exam = Exam.objects.get(id=1)
        self.assertEqual(
            potions_exam.__str__(),
            (
                '(id=1, sa_code=PP, name=Potions Placement, ' +
                'report=(id=1, name=Potions, contact=halfbloodprince@hogwarts.edu), ' +
                'course_id=888888, assignment_id=111111, default_time_filter=2020-06-01 00:00:00+00:00)'
            )
        )

    def test_submission_string_method(self):
        """
        Submission string method should present all variables, and nested Exam and Report objects, in the
        correct format.
        """

        potions_submission = Submission.objects.get(id=1)
        self.assertEqual(
            potions_submission.__str__(),
            (
                '(id=1, submission_id=123456, exam=' +
                '(id=1, sa_code=PP, name=Potions Placement, ' +
                'report=(id=1, name=Potions, contact=halfbloodprince@hogwarts.edu), ' +
                'course_id=888888, assignment_id=111111, default_time_filter=2020-06-01 00:00:00+00:00), ' +
                'student_uniqname=hpotter, submitted_timestamp=2020-06-12 08:15:30+00:00, ' +
                'graded_timestamp=2020-06-12 09:30:15+00:00, score=100.0, ' +
                'transmitted=True, transmitted_timestamp=2020-06-12 12:00:30+00:00)'
            )
        )


class CustomMethodsTestCase(TestCase):
    fixtures: List[str] = ['test_01.json', 'test_04.json']

    def test_get_last_sub_graded_datetime_with_submissions(self):
        potions_exam = Exam.objects.get(id=1)
        last_sub_graded_dt: datetime = potions_exam.get_last_sub_graded_datetime()
        self.assertTrue(last_sub_graded_dt, datetime(2020, 6, 12, 12, 0, 30, tzinfo=utc))

    def test_submission_prepare_score(self):
        sub_two: Submission = Submission.objects.get(submission_id=123457)

        self.assertEqual(
            sub_two.prepare_score(),
            {
                'ID': 'hgranger',
                'Form': 'PP',
                'GradePoints': '300.0'
            }
        )
