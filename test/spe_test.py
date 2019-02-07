import logging
import os
import shutil
import unittest
from autologging import logged
import datetime
from dotenv import load_dotenv
from exam_date.stored_date import AssignmentLatestSubmittedDate
from scores_orchestration.orchestration import SpanishScoresOrchestration
import json
from spe_utils import utils

logging.basicConfig(level=os.getenv("log_level", "DEBUG"))
load_dotenv(dotenv_path=os.path.dirname(os.path.abspath(__file__))[:-4] + "/.env")


@logged
class TestSPEProcess(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.__log.info("you got into the testing zone")
        self.persisted_dir: str = '/tmp/PERSIST'
        self.file_name: str = 'test_persisted.txt'
        self.submitted_date: str = '2019-01-01T22:11:41Z'
        self.date_holder = AssignmentLatestSubmittedDate(self.persisted_dir, self.file_name)
        self.score_handler: SpanishScoresOrchestration = SpanishScoresOrchestration(self.submitted_date)

    def _check_date_format(self, utc_date: str):
        try:
            datetime.datetime.strptime(utc_date, '%Y-%m-%dT%H:%M:%SZ')
            return "Date is in correct format"
        except ValueError:
            raise ValueError("Incorrect data format")

    def test_dir_and_file_created(self):
        """
        this is testing if the persisted.txt dir and file created and see if data is in the format
        %Y-%m-%dT%H:%M:%SZ. deleting the dir only if exist for making the test case still relevant
        for subsequent runs
        :return:
        """
        if os.path.exists(self.persisted_dir):
            shutil.rmtree(self.persisted_dir)
        self.assertEqual(False, os.path.exists(self.persisted_dir))
        # date_holder = AssignmentLatestSubmittedDate(self.persisted_dir, self.file_name)
        latest_test_taken_date = self.date_holder.get_assign_submitted_date()
        self.assertEqual("Date is in correct format", self._check_date_format(latest_test_taken_date))

    def test_write_to_file(self):
        """
        testing persisted.txt return the utc time stamp
        :return:
        """

        with open(self.persisted_dir + '/' + self.file_name, 'w') as f:
            f.write('anything but time')
        # date_holder = AssignmentLatestSubmittedDate(self.persisted_dir, self.file_name)
        date = self.date_holder.get_assign_submitted_date()
        self.assertEqual('anything but time', date)

    def test_strip_end_space_in_date(self):
        with open(self.persisted_dir + '/' + self.file_name, 'w') as f:
            f.write('space_in_end ')
        # date_holder = AssignmentLatestSubmittedDate(self.persisted_dir, self.file_name)
        date = self.date_holder.get_assign_submitted_date()
        self.assertEqual('space_in_end', date)

    def test_strip_begin_space_in_date(self):
        with open(self.persisted_dir + '/' + self.file_name, 'w') as f:
            f.write(' space_in_front')
        # date_holder = AssignmentLatestSubmittedDate(self.persisted_dir, self.file_name)
        date = self.date_holder.get_assign_submitted_date()
        self.assertEqual('space_in_front', date)

    def test_get_spanish_scores(self):
        self.__log.info(
            f"test_get_spanish_scores will take time as pulling grades submitted since {self.submitted_date}")
        response = self.score_handler.get_spanish_scores()
        self.assertEqual(response.status_code, 200)

    def test_send_spanish_score(self):
        response = self.score_handler.send_spanish_score(5.0, 'studenttest')
        self.assertEqual(response.status_code, 200)

    def test_increment_persisted_time_by_sec(self):
        increment_date = '2019-01-01T22:11:00Z'
        actual = SpanishScoresOrchestration.get_query_date_increment_decrement_by_sec(increment_date, '+')
        self.assertEqual('2019-01-01T22:11:01Z',actual)

        # increment minute when 59 sec is the case
        increment_date = '2019-01-01T22:11:59Z'
        actual = SpanishScoresOrchestration.get_query_date_increment_decrement_by_sec(increment_date, '+')
        self.assertEqual('2019-01-01T22:12:00Z',actual)

    def test_decrement_persisted_time_by_sec(self):

        decrement_date = '2019-01-01T22:11:00Z'
        actual = SpanishScoresOrchestration.get_query_date_increment_decrement_by_sec(decrement_date, '-')
        self.assertEqual('2019-01-01T22:10:59Z',actual)

        # increment minute when 59 sec is the case
        decrement_date = '2019-01-01T22:11:59Z'
        actual = SpanishScoresOrchestration.get_query_date_increment_decrement_by_sec(decrement_date, '-')
        self.assertEqual('2019-01-01T22:11:58Z',actual)

    def test_submission_date_sort(self):
        actual = []
        for item in self.get_sorted_scores():
            actual.append(item['submitted_date'])
        expected = ['2019-01-11T02:10:13Z','2019-01-12T03:39:14Z','2019-01-15T23:16:06Z','2019-01-15T23:20:24Z','2019-01-15T23:31:12Z',
                    '2019-01-15T23:51:59Z','2019-01-15T23:52:00Z','2019-01-15T23:54:26Z']
        self.assertEqual(expected,actual)

    def get_sorted_scores(self):
        with open('test.json') as f:
            data = f.read()
        f = json.loads(data)
        sorted_list = SpanishScoresOrchestration.sort_scores_by_submitted_date(f)
        return sorted_list

    def test_happy_path_case_getting_next_query_date(self):
        scores = self.get_sorted_scores()
        self.score_handler.sending_scores_manager(scores)
        actual = self.score_handler.next_persisted_query_date
        self.assertEqual('2019-01-15T23:54:26Z', actual)

    def test_writing_next_query_date(self):
        date_to_be_stored: str = '2019-01-15T23:54:26Z'
        self.date_holder.store_next_query_date('2019-01-15T23:54:26Z')
        actual = self.date_holder.read_persisted_file()
        self.assertEqual(date_to_be_stored, actual)

    def test_unhappy_path_all_scores_not_sent(self):
        scores = self.get_sorted_scores()
        self.score_handler.sending_scores_manager(scores, 'test')
        actual = self.score_handler.next_persisted_query_date
        self.assertEqual('2019-01-11T02:10:12Z', actual)

    def test_unhappy_path_few_scores_not_sent(self):
        scores = self.get_sorted_scores()
        self.score_handler.sending_scores_manager(scores, 'test', True)
        actual = self.score_handler.next_persisted_query_date
        self.__log.info(f"test_unhappy_path_few_scores_not_sent: actual result {actual}")
        actual_date = datetime.datetime.strptime(actual, utils.ISO8601_FORMAT)
        list = ['2019-01-11T02:10:13Z','2019-01-12T03:39:14Z','2019-01-15T23:16:06Z','2019-01-15T23:20:24Z','2019-01-15T23:31:12Z',
                    '2019-01-15T23:51:59Z','2019-01-15T23:52:00Z','2019-01-15T23:54:26Z']
        closest_date= min(list, key = lambda x: abs(datetime.datetime.strptime(x, utils.ISO8601_FORMAT)-actual_date))
        expected = SpanishScoresOrchestration.get_query_date_increment_decrement_by_sec(closest_date,'-')
        self.__log.info(f"test_unhappy_path_few_scores_not_sent: expected result {expected}")
        self.assertEqual(expected, actual)








