import os

import pkg_resources

from spe_utils import constants

from typing import Dict, Union, Optional, List, Any
from umich_api.api_utils import ApiUtil
from spe_report.summary import SPESummaryReport
from autologging import logged, traced
from requests import Response
import datetime
import json
import random
from urllib.parse import quote
from spe_utils.utils import Exam
from dateutil import tz
from spe_utils.constants import PLACEMENT, VALIDATION

from spe_utils.constants import DATE_IN_LOCAL_TZ_FORMAT





@logged
@traced
class SpanishScoresOrchestration:

    def __init__(self, persisted_submitted_date: Dict[str, str], spe_report: SPESummaryReport) -> None:
        self.persisted_submitted_date: Dict[str, str] = persisted_submitted_date
        self.client_id: str = os.getenv(constants.API_DIR_CLIENT_ID)
        self.secret: str = os.getenv(constants.API_DIR_SECRET)
        self.url: str = os.getenv(constants.API_DIR_URL)
        self.api_json: str = pkg_resources.resource_filename(__name__, 'apis.json')
        self.api_handler: ApiUtil = ApiUtil(self.url, self.client_id, self.secret, self.api_json)
        self._next_persisted_query_date: Dict[str, str] = dict()
        self.spe_report: SPESummaryReport = spe_report

    @property
    def next_persisted_query_date(self) -> Dict[str, str]:
        """
        getter for _next_persisted_query_date property
        :return:
        """
        return self._next_persisted_query_date

    @next_persisted_query_date.setter
    def next_persisted_query_date(self, value: Exam) -> None:
        """
        setter for _next_persisted_query_date property
        :param value:
        :return:
        """
        self._next_persisted_query_date[value.exam_type]: Dict[str, str] = value.exam_date

    @staticmethod
    def get_query_date_increment_decrement_by_sec(date: str, operation: str) -> str:
        """
        this function handles increment/decrement given date time by one sec.
        :param date: given UTC date in ISO 8601 format
        :param operation: operation like  +, -
        :return: string date
        """
        date: datetime = datetime.datetime.strptime(date, constants.ISO8601_FORMAT)
        if operation is '+':
            date_in_sec_after_operation: str = f"{(date + datetime.timedelta(seconds=1)).isoformat()}Z"
        if operation is '-':
            date_in_sec_after_operation: str = f"{(date - datetime.timedelta(seconds=1)).isoformat()}Z"
        return date_in_sec_after_operation

    def get_spanish_scores(self, course_id: str, assignment_id: str, canvas_query_date: str, exam_type: str) -> Optional[Response]:
        """
        getting the spanish scores in a course for an assignment
        :return: Response object or None in case of exception
        """
        get_scores_url: str = f"aa/CanvasReadOnly/courses/{course_id}/students/submissions"
        payload: Dict[str, str] = {
            'student_ids[]': 'all',
            'assignment_ids[]': assignment_id,
            'per_page': '100',
            'include[]': 'user',
            'submitted_since': canvas_query_date
        }
        # adding email report details as data get available
        self.spe_report.used_query_date[exam_type] = canvas_query_date
        self.spe_report.stored_persisted_date = self.persisted_submitted_date
        self.spe_report.course_id[exam_type] = course_id

        self.__log.info(
            f"Getting grades for exam_type/{exam_type}/course/{course_id}/assignment/{assignment_id}/query_date/{canvas_query_date}")
        try:
            response: Response = self.api_handler.api_call(get_scores_url, 'canvasreadonly', 'GET', payload)
        except (AttributeError, Exception) as e:
            self.__log.error(f"get spanish score has some error due to {e} ")
            return None
        return response

    def _ready_to_send_score(self, res: Union[Response, None]) -> bool:
        """
        this is checking all the possibilities of Response object types returned
        :param res: requests Response object or None
        :return: bool
        """
        if res is None:
            # returning with no error msg here but logging it before
            return False

        if not res.ok:
            self.__log.error(f"getting spanish scores failed with status code of {res.status_code} due to {res.text}")
            return False

        if not res.text:
            self.__log.info(f"Don't have any new spanish scores submitted since {self.persisted_submitted_date}")
            return False
        return True

    def _is_sending_score_success(self, res: Union[Response, None], user_score: str, user: str, env: str,
                                  enable_randomizer: bool) -> bool:
        """
        This is checking the possibility option that a response sent after sending grades.
        This also simulates failure of the sending a score for testing purposes only
        :param res: Response object or None
        :param user_score: score in spanish test
        :param user: unique name
        :param env: this parameter is for testing purpose would work with string 'test'
        :param enable_randomizer: again for testing purpose, decides whether to randomizes bool options
        :return: bool
        """
        success = False

        if env == constants.TEST:
            if enable_randomizer:
                success = random.choice([True, False])

            if not success:
                self.__log.error(f"Failure Emulation: sending spanish score {user_score} for user {user} failed!")
            return success

        if res is None:
            # returning with no error msg here but logging it before
            return success

        if not res.ok:
            self.__log.error(f"""sending spanish score {user_score} for user {user} failed with
                                 status code of {res.status_code} due to {res.text}""")
            return success

        success = True

        return success

    def send_spanish_score(self, score: float, student_id: str, exam_type: str, form_type: str) -> Union[Response, None]:
        """
        sending a student spanish score to Mpathways
        :param score:
        :param student_id:
        :param exam_type: possible values place|val
        :param form_type: possible values place(7)|val(S)
        :return: Response object or None in case of exception
        """
        send_scores_url: str = f"aa/SpanishPlacementScores/UniqName/{quote(student_id)}/Score/{score}/FormType/{form_type}"
        try:
            response: Response = self.api_handler.api_call(send_scores_url, 'spanishplacementscores', 'PUT')
        except(AttributeError, Exception) as e:
            self.__log.error(f"For Exam type {exam_type}:{form_type} sending spanish score {score} of student {student_id} has some error due to {e} ")
            return None
        return response

    @staticmethod
    def sort_scores_by_submitted_date(scores: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        The function sorts the list based on the `submitted_date` attribute in json
        :type scores: deserialized json response to python list object
        """
        extracted_scores_list: List[Dict[str, str]] = []
        for score in scores:
            utc_submitted_date = score['submitted_at']
            local_submitted_date = SpanishScoresOrchestration.utc_local_timezone(utc_submitted_date)
            extracted_score_dict: Dict[str, str] = {'score': score['score'], 'user': score['user']['login_id'],
                                                    'submitted_date': utc_submitted_date,
                                                    'local_submitted_date': local_submitted_date}
            extracted_scores_list.append(extracted_score_dict)
        extracted_scores_list.sort(key=lambda r: r['submitted_date'])
        return extracted_scores_list

    @staticmethod
    def utc_local_timezone(utc_date):
        from_zone = tz.gettz(constants.UTC)
        to_zone = tz.gettz(constants.EASTERN_TZ)
        utc: datetime = datetime.datetime.strptime(utc_date, constants.ISO8601_FORMAT).replace(tzinfo=from_zone)
        local_datetime: str = utc.astimezone(to_zone).strftime(DATE_IN_LOCAL_TZ_FORMAT)
        return local_datetime

    def sending_scores_manager(self, scores: List[Dict[str, str]], exam_type: str, form_type: str, env: str = None,
                               enable_randomizer: str = False) -> None:
        """
        this function handles sending score to mpathways one at a time. If for reasons
        scores sent has error response then this keep track for the not sent list and
        stores the next query date based on from the list.

        :param exam_type: what type of spanish exam, place or val
        :param form_type: what type of spanish form, place(7) or val(S)
        :param scores: sorted list of dict values holding scores, user, submitted_user_score_date
        :param env: this parameter is for testing purpose would work with string 'test'
        :param enable_randomizer: again for testing purpose, decides whether to randomizes bool options
        :return:
        """
        self.__log.info(f"Mocking a Failure: {str(enable_randomizer)}")

        # iterating over the list and sending one score at a time
        scores_sent_list: List[Dict[str, str]] = []
        scores_future_sent_list: List[Dict[str, str]] = []
        for score in scores:
            user_score: str = score['score']
            user: str = score['user']
            res: Response = self.send_spanish_score(user_score, user, exam_type, form_type)

            if self._is_sending_score_success(res, user_score, user, env, enable_randomizer):
                    self.next_persisted_query_date= Exam(exam_type=exam_type,exam_date=score['submitted_date'])
                    self.__log.info(f"{self.next_persisted_query_date}")

                    self.__log.info(
                       f"For exam type: {exam_type} sending user: {user} score: {user_score} submitted at {score['submitted_date']} is success! ")

                    scores_sent_list.append(score)
            else:
                scores_future_sent_list: List[Dict[str, str]] = [single_score for single_score in scores if
                                                                      single_score not in scores_sent_list]
                # we don't want to send further grades after error while iterating since next run of the cron process
                # should start from the first user score error earlier. Duplicate record sent from our process will
                # end as duplicates in Mpathways system and needs a manual correction
                break

        self.spe_report.full_score_list[exam_type] = scores
        self.spe_report.sent_score_list[exam_type] = scores_sent_list
        self.spe_report.not_sent_scores_list[exam_type] = scores_future_sent_list

        self.__log.debug(f"scores_sent_list: {scores_sent_list}")
        self.__log.debug(f"future_sent_list: {scores_future_sent_list}")
        self.__log.info(f"For Exam Type: '{exam_type}' grades_received/grades_sent: {len(scores)}/{len(scores_sent_list)}")

    def next_date_decider(self):
        stored_exam_types = set(self.next_persisted_query_date.keys())
        local_exam_types = set([PLACEMENT, VALIDATION])

        if not self.next_persisted_query_date:
            self.__log.info("Cron run resulted in fetching no exam scores")
            for exam_type, date in self.persisted_submitted_date.items():
                self.next_persisted_query_date = Exam(exam_type=exam_type, exam_date=date)
            return
        if local_exam_types == stored_exam_types:
            self.__log.info("Cron run resulted in fetching both exam scores")
            return
        if PLACEMENT not in stored_exam_types:
            self.set_next_persisted_query_date(PLACEMENT)
            return
        if VALIDATION not in stored_exam_types:
            self.set_next_persisted_query_date(VALIDATION)
            return

    def set_next_persisted_query_date(self, exam_type):
        self.__log.info(f"Cron run resulted in fetching no '{exam_type}' exam scores")
        self.next_persisted_query_date = Exam(exam_type=exam_type, exam_date=self.persisted_submitted_date[exam_type])

    def orchestrator(self) -> Dict[str, str]:
        """
        Orchestrator role is managing the getting and sending of the scores.
        :return: next query date to be stored
        """
        for exam_type, date in self.persisted_submitted_date.items():
            course_id: str = os.getenv(f"sp_{exam_type}_course")
            assignment_id: str = os.getenv(f"sp_{exam_type}_assignment")
            canvas_query_date: str = SpanishScoresOrchestration.get_query_date_increment_decrement_by_sec(date, '+')
            self.__log.info(f"******************** EXAM TYPE: {exam_type} ***********************")
            scores_resp: Union[Response, None] = self.get_spanish_scores(course_id, assignment_id, canvas_query_date, exam_type)

            if not self._ready_to_send_score(scores_resp):
                # returning with no error msg here but logging it before
                return

            scores_json: List[Dict[str, Any]] = json.loads(scores_resp.text)

            self.__log.info(
                f"For Exam Type '{exam_type}' {len(scores_json)} grades received with latest submission date: {date}")
            scores: List[Dict[str, str]] = self.sort_scores_by_submitted_date(scores_json)
            self.__log.info(f"""The received grades sorted list: 
            {scores}""")

            if not scores_json:
                self.__log.info(f"There are no new scores yet for exam type '{exam_type}' for date {date}")
                continue
            # these 2 variables are testing purposes and won't be needed in Prod env. unit tests are written demonstrating
            # the usecase of the variables.
            enable_randomizer: str = os.getenv(constants.SCORE_RANDOMIZER_FOR_TEST)
            env: str = os.getenv(constants.ENV)
            if exam_type == PLACEMENT:
                form_type = '7'
            if exam_type == VALIDATION:
                form_type = 'S'
            self.sending_scores_manager(scores, exam_type, form_type, env, enable_randomizer)
        self.next_date_decider()
        return self.next_persisted_query_date
