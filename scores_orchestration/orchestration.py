import os

import pkg_resources

from spe_utils import utils

from typing import Dict, Union, Optional
from umich_api.api_utils import ApiUtil
from autologging import logged, traced
from requests import Response
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

    def get_spanish_scores(self) -> Union[Response, None]:
        """
        getting the spanish scores in a course for an assignment
        :return: Response object or None in case of exception
        """
        course_id: str = os.getenv(utils.COURSE_ID)
        assignment_id: str = os.getenv(utils.ASSIGNMENT_ID)
        get_scores_url: str = f"aa/CanvasReadOnly/courses/{course_id}/students/submissions"
        payload: Dict[str, str] = {
            'student_ids[]': 'all',
            'assignment_ids[]': assignment_id,
            'per_page': '100',
            'include[]': 'user',
            'submitted_since': self.persisted_submitted_date
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

    def orchestrator(self):
        scores_resp: Union[Response, None] = self.get_spanish_scores()
        if not self._ready_to_send_score(scores_resp):
            # returning with no error msg here but logging it before
            return
        scores = json.loads(scores_resp.text)
        for score in scores:
            self.send_spanish_score(score['score'], score['user']['login_id'])
