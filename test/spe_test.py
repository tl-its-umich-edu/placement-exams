import logging
import os
import shutil
import unittest
from typing import Dict

from autologging import logged
from datetime import datetime
from dotenv import load_dotenv
from exam_date.stored_date import AssignmentLatestSubmittedDate
from scores_orchestration.orchestration import SpanishScoresOrchestration
from spe_report.summary import SPESummaryReport
from spe_utils.constants import PLACEMENT, VALIDATION
import json

logging.basicConfig(level=os.getenv("log_level", "DEBUG"))
load_dotenv(dotenv_path=os.path.dirname(os.path.abspath(__file__))[:-4] + "/.env")


@logged
class TestSPEProcess(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.__log.info("you got into the testing zone")
        self.persisted_dir: str = '/tmp/PERSIST'
        self.file_name: str = 'test_persisted.json'
        self.submitted_date: Dict[str, str] = {PLACEMENT: '2019-01-01T22:11:41Z', VALIDATION: '2019-01-01T22:11:41Z'}
        self.date_holder = AssignmentLatestSubmittedDate(self.persisted_dir, self.file_name)
        self.score_handler: SpanishScoresOrchestration = SpanishScoresOrchestration(self.submitted_date,
                                                                                    SPESummaryReport())

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
        latest_test_taken_date: Dict[str, str] = self.date_holder.get_assign_submitted_date()
        self.assertEquals(True, self._contains_both_exam_types_in_persisted(latest_test_taken_date))
        self.assertEqual("Date is in correct format", self._check_date_format(latest_test_taken_date))

    def test_write_to_file(self):
        """
        testing persisted.txt return the utc time stamp
        :return:
        """

        with open(self.persisted_dir + '/' + self.file_name, 'w') as f:
            f.write(json.dumps(self.submitted_date))
        date: Dict[str, str] = self.date_holder.get_assign_submitted_date()
        self.assertEquals(dict, type(date))
        self.assertEqual(self.submitted_date, date)

    def test_strip_end_space_in_date(self):
        with open(self.persisted_dir + '/' + self.file_name, 'w') as f:
            f.write('{"place": "2019-01-02T22:11:41Z", "val": "2019-01-02T22:11:41Z"}   ')
        date = self.date_holder.read_persisted_file()
        self.assertEqual('{"place": "2019-01-02T22:11:41Z", "val": "2019-01-02T22:11:41Z"}', date)

    def test_strip_begin_space_in_date(self):
        with open(self.persisted_dir + '/' + self.file_name, 'w') as f:
            f.write(' {"place": "2019-01-03T22:11:41Z", "val": "2019-01-03T22:11:41Z"}')
        date = self.date_holder.read_persisted_file()
        self.assertEqual('{"place": "2019-01-03T22:11:41Z", "val": "2019-01-03T22:11:41Z"}', date)

    def test_get_spanish_placement_scores(self):
        self.__log.info(
            f"test_get_spanish_scores placement will take time as pulling grades submitted since 2019-09-05T14:04:42Z")
        response = self.score_handler.get_spanish_scores(os.getenv('sp_place_course'), os.getenv('sp_place_assignment'),
                                                         '2019-09-05T14:04:42Z', PLACEMENT)
        self.assertEqual(response.status_code, 200)

    def test_get_spanish_validation_scores(self):
        self.__log.info(
            f"test_get_spanish_scores validation will take time as pulling grades submitted since 2019-09-05T14:04:42Z")
        response = self.score_handler.get_spanish_scores(os.getenv('sp_val_course'), os.getenv('sp_val_assignment'),
                                                         '2019-10-05T14:04:42Z', VALIDATION)
        self.assertEqual(response.status_code, 200)

    def test_send_spanish_score(self):
        response = self.score_handler.send_spanish_score(5.0, 'studenttest', VALIDATION, 'S')
        self.assertEqual(response.status_code, 200)

    def test_send_spanish_score_with_friend_account(self):
        response = self.score_handler.send_spanish_score(5.0, 'friendemail+aaps.k12.mi.us', PLACEMENT, '7')
        self.assertEqual(response.status_code, 200)

    def test_send_spanish_score_with_accented_name(self):
        response = self.score_handler.send_spanish_score(5.0, 'HellöWörld', PLACEMENT, '7')
        self.assertEqual(response.status_code, 200)

    def test_increment_persisted_time_by_sec(self):
        increment_date = '2019-01-01T22:11:00Z'
        actual = SpanishScoresOrchestration.get_query_date_increment_decrement_by_sec(increment_date, '+')
        self.assertEqual('2019-01-01T22:11:01Z', actual)

        # increment minute when 59 sec is the case
        increment_date = '2019-01-01T22:11:59Z'
        actual = SpanishScoresOrchestration.get_query_date_increment_decrement_by_sec(increment_date, '+')
        self.assertEqual('2019-01-01T22:12:00Z', actual)

    def test_decrement_persisted_time_by_sec(self):

        decrement_date = '2019-01-01T22:11:00Z'
        actual = SpanishScoresOrchestration.get_query_date_increment_decrement_by_sec(decrement_date, '-')
        self.assertEqual('2019-01-01T22:10:59Z', actual)

        # increment minute when 59 sec is the case
        decrement_date = '2019-01-01T22:11:59Z'
        actual = SpanishScoresOrchestration.get_query_date_increment_decrement_by_sec(decrement_date, '-')
        self.assertEqual('2019-01-01T22:11:58Z', actual)

    def test_place_submission_date_sort(self):
        """
        the test for sorting of the grades received from the GET call. We are not making any API call to get the
        grades but reading from the test.json for convenience
        :return:
        """
        actual = []
        for item in self.get_sorted_scores(PLACEMENT):
            actual.append(item['submitted_date'])
        expected = ['2019-01-11T02:10:13Z', '2019-01-12T03:39:14Z', '2019-01-15T23:16:06Z', '2019-01-15T23:20:24Z',
                    '2019-01-15T23:31:12Z',
                    '2019-01-15T23:51:59Z', '2019-01-15T23:52:00Z', '2019-01-15T23:54:26Z']
        self.assertEqual(expected, actual)

    def test_happy_path_case_getting_next_query_date_place_exam(self):
        """
        The catch here is that SpanishPlacementScores end point should be up and running i.e should receive 200 OK response
        :return:
        """
        submitted_date: Dict[str, str] = {PLACEMENT: '2019-01-01T22:11:41Z', VALIDATION: '2019-01-05T22:11:41Z'}
        score_handler: SpanishScoresOrchestration = SpanishScoresOrchestration(submitted_date, SPESummaryReport())
        # Placement
        scores = self.get_sorted_scores(PLACEMENT)
        score_handler.sending_scores_manager(scores, PLACEMENT, '7')
        actual = score_handler.next_persisted_query_date[PLACEMENT] if score_handler.next_persisted_query_date else None
        self.assertEqual('2019-01-15T23:54:26Z', actual)
        # Validation
        scores = self.get_sorted_scores(VALIDATION)
        score_handler.sending_scores_manager(scores, VALIDATION, 'S')
        actual = score_handler.next_persisted_query_date[
            VALIDATION] if score_handler.next_persisted_query_date else None
        self.assertEqual('2019-02-15T23:54:26Z', actual)

    def test_writing_next_query_date(self):
        date_to_be_stored: Dict[str, str] = {PLACEMENT: '2019-01-15T23:54:26Z', VALIDATION: '2019-01-15T23:54:26Z'}
        self.date_holder.store_next_query_date(date_to_be_stored)
        actual = self.date_holder.read_persisted_file()
        self.assertEqual(json.dumps(date_to_be_stored), actual)

    def test_unhappy_path_first_sent_item_failure(self):
        """
        If the very first item in the scores sending list fail then we don't write anything to persisted.txt
        but just keep what is there
        :return:
        """
        scores = self.get_sorted_scores(PLACEMENT)
        self.score_handler.sending_scores_manager(scores, PLACEMENT, '7', 'test')
        actual = self.score_handler.persisted_submitted_date[PLACEMENT]
        self.__log.debug(f"test_unhappy_path_first_sent_item_Placement_failure:=> actual {actual}")
        self.assertEqual(self.submitted_date[PLACEMENT], actual)

        scores = self.get_sorted_scores(VALIDATION)
        self.score_handler.sending_scores_manager(scores, VALIDATION, 'S', 'test')
        actual = self.score_handler.persisted_submitted_date[VALIDATION]
        self.__log.debug(f"test_unhappy_path_first_sent_item_Validation_failure:=> actual {actual}")
        self.assertEqual(self.submitted_date[VALIDATION], actual)

        self.score_handler.next_date_decider()
        self.assertEqual({PLACEMENT: '2019-01-01T22:11:41Z', VALIDATION: '2019-01-01T22:11:41Z'},
                         self.score_handler.next_persisted_query_date)

    def test_unhappy_path_few_scores_not_sent(self):
        """
        Just doing the placement score testing the logic is exactly same for validation since it is just iteration dict
        items in the orchestration.py#L272
        :return:
        """
        submitted_date: Dict[str, str] = {PLACEMENT: '2019-01-01T22:11:41Z', VALIDATION: '2019-01-05T22:11:41Z'}
        score_handler: SpanishScoresOrchestration = SpanishScoresOrchestration(submitted_date, SPESummaryReport())
        scores = self.get_sorted_scores(PLACEMENT)
        self.__log.info(f"sorted_list: {scores}")
        score_handler.sending_scores_manager(scores, PLACEMENT, '7', 'test', True)
        actual_placement_list = ['2019-01-11T02:10:13Z', '2019-01-12T03:39:14Z', '2019-01-15T23:16:06Z',
                                 '2019-01-15T23:20:24Z',
                                 '2019-01-15T23:31:12Z', '2019-01-15T23:51:59Z', '2019-01-15T23:52:00Z',
                                 '2019-01-15T23:54:26Z']

        scores_future_place_sent_list_len = len(score_handler.spe_report.not_sent_scores_list[PLACEMENT])
        scores_sent_place_list_len = len(score_handler.spe_report.sent_score_list[PLACEMENT])
        actual_place_list_len = len(actual_placement_list)

        if scores_future_place_sent_list_len == 0:
            self.__log.info("TestCase: all the scores sent")
            self.assertEqual('2019-01-15T23:54:26Z', score_handler.next_persisted_query_date[PLACEMENT])
            return
        if scores_future_place_sent_list_len == actual_place_list_len:
            self.__log.info(
                "TestCase: none of the scores sent, matches the test cases \"test_unhappy_path_few_scores_not_sent\"")
            actual = score_handler.persisted_submitted_date[PLACEMENT]
            self.assertEqual(submitted_date[PLACEMENT], actual)
            return

        if scores_future_place_sent_list_len > 0:
            self.__log.info("TestCase: starts out with few success sent and fail later")
            self.__log.info(f"scores_sent_list {score_handler.spe_report.sent_score_list[PLACEMENT]}")
            self.__log.info(f"scores_future_sent_list_len {score_handler.spe_report.not_sent_scores_list[PLACEMENT]}")
            actual = score_handler.next_persisted_query_date[PLACEMENT]
            # minus one since list is zero indexed
            expected = actual_placement_list[scores_sent_place_list_len - 1]
            self.assertEqual(expected, actual)

    def test_next_persisted_date_has_both_exam_types_no_scores_sent(self):
        submitted_date: Dict[str, str] = {PLACEMENT: '2019-01-01T22:11:41Z', VALIDATION: '2019-01-05T22:11:41Z'}
        score_handler: SpanishScoresOrchestration = SpanishScoresOrchestration(submitted_date, SPESummaryReport())

        scores = self.get_sorted_scores(PLACEMENT)
        score_handler.sending_scores_manager(scores, PLACEMENT, '7', 'test')
        scores = self.get_sorted_scores(VALIDATION)
        score_handler.sending_scores_manager(scores, VALIDATION, 'S', 'test')
        self.assertEqual({}, score_handler.next_persisted_query_date)
        score_handler.next_date_decider()
        self.assertEqual(submitted_date, score_handler.next_persisted_query_date)

    def test_next_persisted_date_has_both_exam_types_no_val_score_sent(self):
        submitted_date: Dict[str, str] = {PLACEMENT: '2019-01-01T22:11:41Z', VALIDATION: '2019-01-05T22:11:41Z'}
        score_handler: SpanishScoresOrchestration = SpanishScoresOrchestration(submitted_date, SPESummaryReport())

        place_scores = self.get_sorted_scores(PLACEMENT)
        score_handler.sending_scores_manager(place_scores, PLACEMENT, '7')
        val_scores = self.get_sorted_scores(VALIDATION)
        score_handler.sending_scores_manager(val_scores, VALIDATION, 'S', 'test')
        score_handler.next_date_decider()
        expected: Dict[str, str] = {PLACEMENT: '2019-01-15T23:54:26Z', VALIDATION: '2019-01-05T22:11:41Z'}
        self.assertEqual(expected, score_handler.next_persisted_query_date)

    def test_next_persisted_date_has_both_exam_types_no_place_score_sent(self):
        submitted_date: Dict[str, str] = {PLACEMENT: '2019-01-01T22:11:41Z', VALIDATION: '2019-01-05T22:11:41Z'}
        score_handler: SpanishScoresOrchestration = SpanishScoresOrchestration(submitted_date, SPESummaryReport())

        place_scores = self.get_sorted_scores(PLACEMENT)
        score_handler.sending_scores_manager(place_scores, PLACEMENT, '7', 'test')
        val_scores = self.get_sorted_scores(VALIDATION)
        score_handler.sending_scores_manager(val_scores, VALIDATION, 'S')
        score_handler.next_date_decider()
        expected: Dict[str, str] = {PLACEMENT: '2019-01-01T22:11:41Z', VALIDATION: '2019-02-15T23:54:26Z'}
        self.assertEqual(expected, score_handler.next_persisted_query_date)

    def test_no_scores_received_email_summary_subject(self):
        """
        This is the case when both placement and validation don't have new scores received from the query date
        you might see occasional failure(but rare) due to second shift when calculating now()
        :return:
        """
        report1: SPESummaryReport = SPESummaryReport()
        actual = report1.get_subject()
        date_now = datetime.now().replace(microsecond=0)
        expected = f"P(0/0):V(0/0) Spanish Placement Exam Processing Summary {date_now}"
        self.assertEqual(expected, actual)

    def test_email_subject_when_only_placement_score_received(self):
        """
        This is the case when only placement scores fetched and not validation from a query date
        you might see a occasional failure( but rare) due to second shift when calculating now()
        :return:
        """
        report2: SPESummaryReport = SPESummaryReport()
        report2.full_score_list[PLACEMENT] = self.get_place_score()
        report2.sent_score_list[PLACEMENT] = self.get_place_score()
        actual = report2.get_subject()
        date_now = datetime.now().replace(microsecond=0)
        expected = f"P(4/4):V(0/0) Spanish Placement Exam Processing Summary {date_now}"
        self.assertEqual(expected, actual)

    def test_email_subject_when_only_validation_score_received(self):
        """
        This is the case when only validation scores fetched and not placement from a query date
        you might see a occasional failure( but rare) due to second shift when calculating now()
        :return:
        """
        report3: SPESummaryReport = SPESummaryReport()
        report3.full_score_list[VALIDATION] = self.get_val_score()
        report3.sent_score_list[VALIDATION] = self.get_val_score()
        actual = report3.get_subject()
        date_now = datetime.now().replace(microsecond=0)
        expected = f"P(0/0):V(5/5) Spanish Placement Exam Processing Summary {date_now}"
        self.assertEqual(expected, actual)

    def test_email_subject_few_failure_sending_placement_validation_scores(self):
        report4: SPESummaryReport = SPESummaryReport()
        report4.full_score_list = self.get_full_score()
        report4.sent_score_list = {PLACEMENT: self.get_place_score()[0:3], VALIDATION: self.get_val_score()[0:4]}
        actual = report4.get_subject()
        date_now = datetime.now().replace(microsecond=0)
        expected = f"P(3/4):V(4/5) Spanish Placement Exam Processing Summary {date_now}"
        self.assertEqual(expected, actual)

    def test_email_subject_scores_received_no_placement_scores_not_sent(self):
        report4: SPESummaryReport = SPESummaryReport()
        report4.full_score_list = self.get_full_score()
        report4.sent_score_list[VALIDATION] = self.get_val_score()[0:4]
        actual = report4.get_subject()
        date_now = datetime.now().replace(microsecond=0)
        expected = f"P(0/4):V(4/5) Spanish Placement Exam Processing Summary {date_now}"
        self.assertEqual(expected, actual)

    def test_email_subject_scores_received_no_validation_scores_not_sent(self):
        report5: SPESummaryReport = SPESummaryReport()
        report5.full_score_list = self.get_full_score()
        report5.sent_score_list[PLACEMENT] = self.get_place_score()[0:2]
        actual = report5.get_subject()
        date_now = datetime.now().replace(microsecond=0)
        expected = f"P(2/4):V(0/5) Spanish Placement Exam Processing Summary {date_now}"
        self.assertEqual(expected, actual)

    def test_utc_local(self):
        actual = SpanishScoresOrchestration.utc_local_timezone('2011-01-21T02:37:21Z')
        expected = '2011-01-20 21:37:21-0500'
        self.assertEqual(expected, actual)

    def test_scores_received(self):
        report6: SPESummaryReport = SPESummaryReport()
        # full_score_list variable will be empty now
        self.assertEqual(False, report6.is_any_scores_received())
        #  received both placement and validation scores
        report6.full_score_list = self.get_full_score()
        self.assertEqual(True, report6.is_any_scores_received())
        # only received Validation scores
        report6.full_score_list = {VALIDATION: self.get_val_score(), PLACEMENT: []}
        self.assertEqual(True, report6.is_any_scores_received())
        # only received placement scores
        report6.full_score_list = {VALIDATION: [], PLACEMENT: self.get_place_score()}
        self.assertEqual(True, report6.is_any_scores_received())

    @staticmethod
    def get_sorted_scores(exam_type: str):
        """
        reading the sample sample of json that reflect a sample of from the GET API call. This method will be reused
        when testing the date with grades
        :return:
        """
        absolute_path = os.path.dirname(os.path.abspath(__file__))
        with open(f'{absolute_path}/test_{exam_type}.json') as f:
            data = f.read()
        scores = json.loads(data)
        sorted_list = SpanishScoresOrchestration.sort_scores_by_submitted_date(scores)
        return sorted_list

    @staticmethod
    def _check_date_format(utc_date: Dict[str, str]):
        try:
            if (datetime.strptime(utc_date[PLACEMENT], '%Y-%m-%dT%H:%M:%SZ') and
                    datetime.strptime(utc_date[VALIDATION], '%Y-%m-%dT%H:%M:%SZ')):
                return "Date is in correct format"
        except ValueError:
            raise ValueError("Incorrect data format")

    @staticmethod
    def _contains_both_exam_types_in_persisted(date):
        count = 0
        exam_type = [PLACEMENT, VALIDATION]
        for key in date.keys():
            if key in exam_type:
                count += 1
        if count == 2:
            return True
        else:
            return False

    @staticmethod
    def get_full_score():
        return {'place': [{'score': 5.0, 'user': 'studa', 'submitted_date': '2019-01-04T16:58:14Z'},
                          {'score': 5135.4, 'user': 'studb', 'submitted_date': '2019-01-09T20:00:25Z'},
                          {'score': 1718.2, 'user': 'studc', 'submitted_date': '2019-01-09T21:40:20Z'},
                          {'score': 5032.3, 'user': 'studd', 'submitted_date': '2019-01-09T21:41:38Z'}],
                'val': [{'score': 2831.4, 'user': 'stude', 'submitted_date': '2019-01-09T21:52:02Z'},
                        {'score': 2729.1, 'user': 'studf', 'submitted_date': '2019-01-09T21:53:08Z'},
                        {'score': 1325.0, 'user': 'studg', 'submitted_date': '2019-01-09T21:54:17Z'},
                        {'score': 1928.2, 'user': 'studh', 'submitted_date': '2019-01-09T21:54:35Z'},
                        {'score': 1211.0, 'user': 'studi', 'submitted_date': '2019-01-10T21:33:51Z'}]}

    @staticmethod
    def get_place_score():
        return [{'score': 5.0, 'user': 'studa', 'submitted_date': '2019-01-04T16:58:14Z'},
                {'score': 5135.4, 'user': 'studb', 'submitted_date': '2019-01-09T20:00:25Z'},
                {'score': 1718.2, 'user': 'studc', 'submitted_date': '2019-01-09T21:40:20Z'},
                {'score': 5032.3, 'user': 'studd', 'submitted_date': '2019-01-09T21:41:38Z'}]

    @staticmethod
    def get_val_score():
        return [{'score': 2831.4, 'user': 'stude', 'submitted_date': '2019-01-09T21:52:02Z'},
                {'score': 2729.1, 'user': 'studf', 'submitted_date': '2019-01-09T21:53:08Z'},
                {'score': 1325.0, 'user': 'studg', 'submitted_date': '2019-01-09T21:54:17Z'},
                {'score': 1928.2, 'user': 'studh', 'submitted_date': '2019-01-09T21:54:35Z'},
                {'score': 1211.0, 'user': 'studi', 'submitted_date': '2019-01-10T21:33:51Z'}]


if __name__ == '__main__':
    unittest.main()
