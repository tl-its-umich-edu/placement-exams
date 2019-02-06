import os

import pkg_resources

from spe_utils import utils

from typing import Dict, Union, Optional, List, Any, Tuple
from umich_api.api_utils import ApiUtil
from autologging import logged, traced
from requests import Response
import datetime
import json


@logged
@traced
class SpanishScoresOrchestration:

    def __init__(self, persisted_submitted_date: str) -> None:
        self.persisted_submitted_date: str = persisted_submitted_date
        self.client_id: str = os.getenv(utils.API_DIR_CLIENT_ID)
        self.secret: str = os.getenv(utils.API_DIR_SECRET)
        self.url: str = os.getenv(utils.API_DIR_URL)
        self.api_json: str = pkg_resources.resource_filename(__name__, 'apis.json')
        self.api_handler: ApiUtil = ApiUtil(self.url, self.client_id, self.secret, self.api_json)
        self._persisted_increment_date = None
        self._next_persisted_query_date = None

    @property
    def next_persisted_query_date(self):
        return self._next_persisted_query_date

    @next_persisted_query_date.setter
    def next_persisted_query_date(self, value):
        self._next_persisted_query_date = value


    def get_query_date_increment_by_sec(self):
        persist_date: datetime = datetime.datetime.strptime(self.persisted_submitted_date, utils.ISO8601_FORMAT)
        increment_date_sec: str = f"{(persist_date + datetime.timedelta(seconds=1)).isoformat()}Z"
        self.persisted_submitted_date = increment_date_sec
        return increment_date_sec

    def get_spanish_scores(self) -> Union[Response, None]:
        """
        getting the spanish scores in a course for an assignment
        :return: Response object or None in case of exception
        """
        course_id: str = os.getenv(utils.COURSE_ID)
        assignment_id: str = os.getenv(utils.ASSIGNMENT_ID)
        canvas_query_date = self.get_query_date_increment_by_sec()
        get_scores_url: str = f"aa/CanvasReadOnly/courses/{course_id}/students/submissions"
        payload: Dict[str, str] = {
            'student_ids[]': 'all',
            'assignment_ids[]': assignment_id,
            'per_page': '100',
            'include[]': 'user',
            'submitted_since': canvas_query_date
        }
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
        :return:
        """
        if not res:
            # returning with no error msg here but logging it before
            return False

        if not res.ok:
            self.__log.error(f"getting spanish scores failed with status code of {res.status_code} due to {res.text}")
            return False

        if not res.text:
            self.__log.info(f" Don't have any new spanish scores submitted since {self.persisted_submitted_date}")
            return False
        return True

    def _sending_score_success(self, res):
        if not res:
            # returning with no error msg here but logging it before
            return False

        if not res.ok:
            self.__log.error(f"sending spanish scores failed with status code of {res.status_code} due to {res.text}")
            return False
        return True


    def send_spanish_score(self, score: float, student_id: str) -> Union[Response, None]:
        """
        sending a student spanish score it Mpathways
        :param score:
        :param student_id:
        :return: Response object or None in case of exception
        """
        send_scores_url: str = f"aa/SpanishPlacementScores/UniqName/{student_id}/Score/{score}"
        try:
            response: Optional[Response] = self.api_handler.api_call(send_scores_url, 'spanishplacementscores', 'PUT')
        except(AttributeError, Exception) as e:
            self.__log.error(f"sending spanish score {score} of student {student_id} has some error due to {e} ")
            return None
        return response

    @staticmethod
    def sort_scores_by_submitted_date(scores):
        """

        :type scores: object
        """
        extracted_scores_list: List[Dict[str, Any]] = []
        for score in scores:
            extracted_score_dict = {'score': score['score'], 'user': score['user']['login_id'],
                                    'submitted_date': score['submitted_at']}
            extracted_scores_list.append(extracted_score_dict)
        extracted_scores_list.sort(key=lambda r: r['submitted_date'])
        return extracted_scores_list

    def sending_scores_manager(self, scores):
        for score in scores:
            res = self.send_spanish_score(score['score'], score['user'])
            if not self._sending_score_success(res):
                return
            self.next_persisted_query_date = score['submitted_date']

    def orchestrator(self):
        scores_resp: Union[Response, None] = self.get_spanish_scores()
        if not self._ready_to_send_score(scores_resp):
            # returning with no error msg here but logging it before
            return
        scores_json = json.loads(scores_resp.text)
        scores = self.sort_scores_by_submitted_date(scores_json)
        self.sending_scores_manager(scores)
        return self.next_persisted_query_date
