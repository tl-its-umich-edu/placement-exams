# standard libraries
import json, logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Union

# third-party libraries
from django.db.models import QuerySet
from django.utils.timezone import utc
from requests import Response
from umich_api.api_utils import ApiUtil

# local libraries
from api_retry.util import api_call_with_retries
from constants import CANVAS_SCOPE, ISO8601_FORMAT, MPATHWAYS_SCOPE
from pe.models import Exam, Submission


LOGGER = logging.getLogger(__name__)


class ScoresOrchestration:

    def __init__(self, api_handler: ApiUtil, exam: Exam) -> None:
        """
        Set the ApiUtil instance and exam as instance variables, then determine the sub_time_filter value.
        
        :param api_handler: Instance of ApiUtil for making API calls
        :type api_handler: ApiUtil
        :param exam: Exam model instance for the exam to be processed
        :type exam: Exam
        :return: None
        :rtype: None
        """
        self.api_handler: ApiUtil = api_handler
        self.exam: Exam = exam

        # Determine sub_time_filter
        last_sub_dt: Union[None, datetime] = self.exam.get_last_sub_graded_datetime()
        if last_sub_dt is None:
            LOGGER.info('No previous submissions found for exam.')
            LOGGER.info(f"Setting submission time filter to the exam default {self.exam.default_time_filter}")
            sub_time_filter: datetime = self.exam.default_time_filter
        else:
            # Increment datetime by one second for filter
            sub_time_filter = last_sub_dt + timedelta(seconds=1)
            LOGGER.info(f'Setting submission time filter to last graded_at value plus one second: {sub_time_filter}')

        self.sub_time_filter: datetime = sub_time_filter

    def get_sub_dicts_for_exam(self, page_size: int = 50) -> List[Dict[str, Any]]:
        """
        Get the graded submissions for self.exam using paging, and then store the results in the database.

        :param page_size: How many results from Canvas to include per page
        :type page_size: int, optional (default is 50)
        :return: List of submission dictionaries from Canvas based on parameters in get_sub_dicts_for_exam
        :rtype: List of dictionaries with string keys
        """
        get_subs_url: str = f'aa/CanvasReadOnly/courses/{self.exam.course_id}/students/submissions'

        canvas_params: Dict[str, Any] = {
            'student_ids': ['all'],
            'assignment_ids': [str(self.exam.assignment_id)],
            'per_page': page_size,
            'include': ['user'],
            'graded_since': self.sub_time_filter.strftime(ISO8601_FORMAT)
        }

        more_pages: bool = True
        page_num: int = 1
        sub_dicts: List[Dict[str, Any]] = []
        next_params: Union[Dict] = canvas_params

        LOGGER.debug(f'params for request: {next_params}')
        while more_pages:
            LOGGER.debug(f'Page number {page_num}')
            response: Union[Response, None] = api_call_with_retries(
                self.api_handler,
                get_subs_url,
                CANVAS_SCOPE,
                'GET',
                next_params
            )
            if response is None:
                LOGGER.info('api_call_with_retries failed to get a response; no more data will be collected')
                more_pages = False
            else:
                sub_dicts += json.loads(response.text)
                page_info: Union[None, Dict[str, Any]] = self.api_handler.get_next_page(response)
                LOGGER.debug(page_info)
                if not page_info:
                    more_pages = False
                else:
                    next_params = page_info
                    page_num += 1
    
        LOGGER.info(f'Gathered {len(sub_dicts)} submissions from Canvas')
        LOGGER.debug(sub_dicts)
        return sub_dicts

    def create_sub_records(self, sub_dicts: List[Dict[str, Any]]) -> None:
        """
        Parses Canvas submission records and write them to the database.

        :return sub_dicts: Dictionary results of Canvas API search in get_sub_dicts_for_exam
        :type sub_dicts: List of dictionaries with string keys
        """
        if len(sub_dicts) == 0:
            LOGGER.info('No sub_dicts were provided')
        else:
            try:
                Submission.objects.bulk_create(
                    objs=[
                        Submission(
                            submission_id=sub_dict['id'],
                            exam=self.exam,
                            student_uniqname=sub_dict['user']['login_id'],
                            submitted_timestamp=sub_dict['submitted_at'],
                            graded_timestamp=sub_dict['graded_at'],
                            score=sub_dict['score'],
                            transmitted=False
                        )
                        for sub_dict in sub_dicts
                    ]
                )
                LOGGER.info(f'Inserted {len(sub_dicts)} new Submission records in the database')
            except Exception as e:
                LOGGER.error(e)
                LOGGER.error('Submissions bulk creation failed')

    def send_scores(self, scores_to_send: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Send student scores in bulk for exam to M-Pathways.

        :param scores_to_send: list of dictionaries with key-value pairs for ID, Form, and GradePoints
        :type scores_to_send: list of dictionaries
        :return: Dictionary of response data return from M-Pathways
        :rtype: Dictionary with string keys
        """
        send_scores_url: str = 'aa/SpanishPlacementScores/Scores'

        payload: Dict[str, Any] = {'putPlcExamScore': {'Student': scores_to_send}}

        json_payload: str = json.dumps(payload)
        LOGGER.debug(json_payload)

        extra_headers = [{'Content-Type': 'application/json'}]

        try:
            response: Response = self.api_handler.api_call(
                send_scores_url,
                MPATHWAYS_SCOPE,
                'PUT',
                payload=json_payload,
                api_specific_headers=extra_headers
            )
        except Exception as e:
            LOGGER.error(e)
            LOGGER.error(f'The bulk upload with the following payload failed: {payload}')

        resp_data: Dict[str, Any] = json.loads(response.text)
        LOGGER.debug(resp_data)
        return resp_data

    def update_sub_records(self, resp_data: Dict[str, Any]) -> None:
        """
        Interpret results of sending scores and update Submissions when scores were successfully transmitted.
        
        :param resp_data: Dictionary containing response data from the M-Pathways API endpoint
        :type resp_data: List of dictionaries
        :return: None
        :rtype: None
        """
        schema_name: str = 'putPlcExamScoreResponse'
        results: Dict[str, Any] = resp_data[schema_name][schema_name]

        if results['BadCount'] > 0:
            LOGGER.warning(f"Discovered {results['BadCount']} record error(s): {results['Errors']}")

        # Hope this can be simplified in the future if API response data can be made to use consistent types
        if results['GoodCount'] > 1:
            success_uniqnames: List[str] = [success_dict['uniqname'] for success_dict in results['Success']]
        elif results['GoodCount'] == 1:
            success_uniqnames = [results['Success']['uniqname']]
        else:
            success_uniqnames = []
        num_success: int = len(success_uniqnames)

        if len(success_uniqnames) == 0:
            LOGGER.warning('No scores were transmitted successfully.')
        else:
            timestamp: datetime = datetime.now(tz=utc)
            subs_to_update_qs: QuerySet = self.exam.submissions.filter(
                transmitted=False,
                student_uniqname__in=success_uniqnames
            )
            subs_to_update_qs.update(transmitted=True, transmitted_timestamp=timestamp)
            LOGGER.info(f'Transmitted {num_success} score(s) and updated submission record(s)')
        return None

    def main(self) -> None:
        """
        High-level process method for class. Pulls Canvas data, sends data, and logs activity in the database.
        
        :return: None
        :rtype: None
        """
        # Fetch data from Canvas API and store as submission records in the database
        sub_dicts: List[Dict[str, Any]] = self.get_sub_dicts_for_exam()
        if len(sub_dicts) > 0:
            self.create_sub_records(sub_dicts)

        # Find old and new submissions for exam to send to M-Pathways.
        sub_to_transmit_qs: QuerySet = self.exam.submissions.filter(transmitted=False)
        subs_to_transmit: List[Submission] = list(sub_to_transmit_qs.all())

        # Identify old submissions for debugging purposes
        redo_subs: List[Submission] = list(sub_to_transmit_qs.filter(graded_timestamp__lt=self.sub_time_filter))
        if len(redo_subs) > 0:
            LOGGER.info(f'Will try to re-send {len(redo_subs)} previously un-transmitted submissions')
            if len(redo_subs) > 10:
                LOGGER.debug(f'First 10 previously un-transmitted submissions: {redo_subs}')
            else:
                LOGGER.debug(f'All previously un-transmitted submissions: {redo_subs}')

        # Send data to M-Pathways and update submission records in database
        score_dicts: List[Dict[str, str]] = [sub.prepare_score() for sub in subs_to_transmit]
        if len(score_dicts) > 0:
            resp_data: Dict[str, Any] = self.send_scores(score_dicts)
            self.update_sub_records(resp_data)
        else:
            LOGGER.info(f'No scores for {self.exam.name} exam need to be transmitted')

        return None
