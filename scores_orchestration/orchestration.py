import os

import pkg_resources

from spe_utils import constants

from typing import Dict, Union, Optional, List, Any
from umich_api.api_utils import ApiUtil
from autologging import logged, traced
from requests import Response
import datetime
import json
import random


@logged
@traced
class SpanishScoresOrchestration:

    def __init__(self, persisted_submitted_date: str) -> None:
        self.persisted_submitted_date: str = persisted_submitted_date
        self.client_id: str = os.getenv(constants.API_DIR_CLIENT_ID)
        self.secret: str = os.getenv(constants.API_DIR_SECRET)
        self.url: str = os.getenv(constants.API_DIR_URL)
        self.api_json: str = pkg_resources.resource_filename(__name__, 'apis.json')
        self.api_handler: ApiUtil = ApiUtil(self.url, self.client_id, self.secret, self.api_json)
        self._next_persisted_query_date = None
        self._scores_sent_list: List[Dict[str, str]] = []
        self._scores_future_sent_list: List[Dict[str, str]] = []

    @property
    def next_persisted_query_date(self) -> str:
        """
        getter for _next_persisted_query_date property
        :return:
        """
        return self._next_persisted_query_date

    @next_persisted_query_date.setter
    def next_persisted_query_date(self, value: str) -> None:
        """
        setter for _next_persisted_query_date property
        :param value:
        :return:
        """
        self._next_persisted_query_date: str = value

    @property
    def scores_sent_list(self) -> List[Dict[str, str]]:
        """
        getter for the _scores_sent_list
        :return:
        """
        return self._scores_sent_list

    @scores_sent_list.setter
    def scores_sent_list(self, value: Dict[str, str]) -> None:
        self._scores_sent_list.append(value)

    @property
    def scores_future_sent_list(self) -> List[Dict[str, str]]:
        return self._scores_future_sent_list

    @scores_future_sent_list.setter
    def scores_future_sent_list(self, value: List[Dict[str, str]]) -> None:
        self._scores_future_sent_list = value

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

    def get_spanish_scores(self) -> Optional[Response]:
        """
        getting the spanish scores in a course for an assignment
        :return: Response object or None in case of exception
        """
        course_id: str = os.getenv(constants.COURSE_ID)
        assignment_id: str = os.getenv(constants.ASSIGNMENT_ID)
        canvas_query_date: str = SpanishScoresOrchestration. \
            get_query_date_increment_decrement_by_sec(self.persisted_submitted_date, '+')
        self.__log.info(f"{self.persisted_submitted_date} Persisted date incremented to 1sec as {canvas_query_date}")
        get_scores_url: str = f"aa/CanvasReadOnly/courses/{course_id}/students/submissions"
        payload: Dict[str, str] = {
            'student_ids[]': 'all',
            'assignment_ids[]': assignment_id,
            'per_page': '100',
            'include[]': 'user',
            'submitted_since': canvas_query_date
        }
        self.__log.info(
            f"Getting grades for course/{course_id}/assignment/{assignment_id}/query_date/{canvas_query_date}")
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

    def send_spanish_score(self, score: float, student_id: str) -> Union[Response, None]:
        """
        sending a student spanish score to Mpathways
        :param score:
        :param student_id:
        :return: Response object or None in case of exception
        """
        send_scores_url: str = f"aa/SpanishPlacementScores/UniqName/{student_id}/Score/{score}"
        try:
            response: Response = self.api_handler.api_call(send_scores_url, 'spanishplacementscores', 'PUT')
        except(AttributeError, Exception) as e:
            self.__log.error(f"sending spanish score {score} of student {student_id} has some error due to {e} ")
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
            extracted_score_dict: Dict[str, str] = {'score': score['score'], 'user': score['user']['login_id'],
                                                    'submitted_date': score['submitted_at']}
            extracted_scores_list.append(extracted_score_dict)
        extracted_scores_list.sort(key=lambda r: r['submitted_date'])
        return extracted_scores_list

    def sending_scores_manager(self, scores: List[Dict[str, str]], env: str = None,
                               enable_randomizer: str = False) -> None:
        """
        this function handles sending score to mpathways one at a time. If for reasons
        scores sent has error response then this keep track for the not sent list and
        stores the next query date based on from the list.

        :param scores: sorted list of dict values holding scores, user, submitted_user_score_date
        :param env: this parameter is for testing purpose would work with string 'test'
        :param enable_randomizer: again for testing purpose, decides whether to randomizes bool options
        :return:
        """

        # iterating over the list and sending one score at a time
        for score in scores:
            user_score: str = score['score']
            user: str = score['user']
            res: Response = self.send_spanish_score(user_score, user)

            if self._is_sending_score_success(res, user_score, user, env, enable_randomizer):
                self.next_persisted_query_date: str = score['submitted_date']
                self.__log.info(
                    f"sending user: {user} score: {user_score} submitted at {score['submitted_date']} is success! ")
                self.scores_sent_list: List[Dict[str, str]] = score
            else:
                self.scores_future_sent_list: List[Dict[str, str]] = [single_score for single_score in scores if
                                                                      single_score not in self.scores_sent_list]
                # we don't want to send further grades after error while iterating since next run of the cron process
                # should start from the first user score error earlier. Duplicate record sent from our process will
                # end as duplicates in Mpathways system and needs a manual correction
                break

        self.__log.debug(f"scores_sent_list: {self.scores_sent_list}")
        self.__log.debug(f"future_sent_list: {self.scores_future_sent_list}")

        self.__log.info(f"grades_received/grades_sent: {len(scores)}/{len(self.scores_sent_list)}")

    def orchestrator(self) -> str:
        """
        Orchestrator role is managing the getting and sending of the scores.
        :return: next query date to be stored
        """
        scores_resp: Union[Response, None] = self.get_spanish_scores()

        if not self._ready_to_send_score(scores_resp):
            # returning with no error msg here but logging it before
            return

        scores_json: List[Dict[str, Any]] = json.loads(scores_resp.text)

        self.__log.info(
            f"{len(scores_json)} grades received with latest submission date: {self.persisted_submitted_date}")
        scores: List[Dict[str, str]] = self.sort_scores_by_submitted_date(scores_json)
        self.__log.info(f"""The received grades sorted list: 
        {scores}""")

        if not scores_json:
            self.__log.info(f"There are no new scores yet for date {self.persisted_submitted_date}")
            return
        # these 2 variables are testing purposes and won't be needed in Prod env. unit tests are written demonstrating
        # the usecase of the variables.
        enable_randomizer: str = os.getenv(constants.SCORE_RANDOMIZER_FOR_TEST)
        env: str = os.getenv(constants.ENV)

        self.sending_scores_manager(scores, env, enable_randomizer)
        return self.next_persisted_query_date
