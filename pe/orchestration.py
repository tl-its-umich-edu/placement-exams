# standard libraries
import json, logging, os
from datetime import datetime, timedelta
from typing import Any, Union

# third-party libraries
from django.db.models import Count, QuerySet
from django.utils.timezone import utc
from requests import Response
from umich_api.api_utils import ApiUtil

# local libraries
from api_retry.util import api_call_with_retries, check_if_response_successful
from constants import (
    CANVAS_SCOPE, CANVAS_URL_BEGIN, ISO8601_FORMAT, MPATHWAYS_SCOPE, MPATHWAYS_URL
)
from pe.models import Exam, Submission
from util import chunk_list


LOGGER = logging.getLogger(__name__)

MAX_REQ_ATTEMPTS = int(os.getenv('MAX_REQ_ATTEMPTS', '3'))


class ScoresOrchestration:
    """
    Utility class for orchestrating the gathering and sending of submission-related data for an exam.
    Submission records are stored in the database and updated according to the results.
    """

    def __init__(self, api_handler: ApiUtil, exam: Exam) -> None:
        """
        Sets the ApiUtil instance and exam as instance variables, then determines the sub_time_filter value.

        :param api_handler: Instance of ApiUtil for making API calls
        :type api_handler: ApiUtil
        :param exam: Exam model instance for the exam to be processed
        :type exam: Exam
        :return: None
        :rtype: None
        """
        self.api_handler: ApiUtil = api_handler
        self.exam: Exam = exam

        last_sub_dt: Union[None, datetime] = self.exam.get_last_sub_graded_datetime()
        if last_sub_dt is None:
            LOGGER.info('No previous submissions found for exam.')
            LOGGER.info(f"Setting submission time filter to the exam default {self.exam.default_time_filter}")
            sub_time_filter: datetime = self.exam.default_time_filter
        else:
            # Increment datetime by one second for filter
            sub_time_filter = last_sub_dt + timedelta(seconds=1)
            LOGGER.info(
                f'Setting submission time filter to last graded_timestamp value plus one second: {sub_time_filter}'
            )
        self.sub_time_filter: datetime = sub_time_filter

    def get_sub_dicts_for_exam(self, page_size: int = 50) -> list[dict[str, Any]]:
        """
        Gets the graded submissions for the exam using paging.

        :param page_size: How many results from Canvas to include per page
        :type page_size: int, optional (default is 50)
        :return: List of submission dictionaries from Canvas returned based on the URL and parameters
        :rtype: List of dictionaries with string keys
        """
        get_subs_url: str = f'{CANVAS_URL_BEGIN}/courses/{self.exam.course_id}/students/submissions'

        canvas_params: dict[str, Any] = {
            'student_ids[]': 'all',
            'assignment_ids[]': str(self.exam.assignment_id),
            'per_page': page_size,
            'include[]': 'user',
            'graded_since': self.sub_time_filter.strftime(ISO8601_FORMAT)
        }

        more_pages: bool = True
        page_num: int = 1
        sub_dicts: list[dict[str, Any]] = []
        next_params: dict[str, Any] = canvas_params
        LOGGER.debug(f'Params for first request: {next_params}')

        while more_pages:
            LOGGER.debug(f'Page number {page_num}')
            response: Union[Response, None] = api_call_with_retries(
                self.api_handler,
                get_subs_url,
                CANVAS_SCOPE,
                'GET',
                next_params,
                MAX_REQ_ATTEMPTS
            )
            if response is None:
                LOGGER.info('api_call_with_retries failed to get a response; no more data will be collected')
                more_pages = False
            else:
                sub_dicts += json.loads(response.text)
                page_info: Union[None, dict[str, Any]] = self.api_handler.get_next_page(response)
                if not page_info:
                    more_pages = False
                else:
                    LOGGER.debug(f'Params for next page: {page_info}')
                    next_params = page_info
                    page_num += 1

        sub_dicts_with_scores: list[dict[str, Any]] = list(filter((lambda x: x['score'] is not None), sub_dicts))
        filter_diff: int = len(sub_dicts) - len(sub_dicts_with_scores)
        if filter_diff > 0:
            LOGGER.info(f'Discarded {filter_diff} Canvas submission(s) with no score(s)')

        LOGGER.info(f'Gathered {len(sub_dicts_with_scores)} submission(s) from Canvas')
        LOGGER.debug(sub_dicts_with_scores)
        return sub_dicts_with_scores

    def create_sub_records(self, sub_dicts: list[dict[str, Any]]) -> None:
        """
        Parses Canvas submission records and writes them to the database.

        :param sub_dicts: Dictionary results of Canvas API search in get_sub_dicts_for_exam
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
                            attempt_num=sub_dict['attempt'],
                            exam=self.exam,
                            student_uniqname=sub_dict['user']['login_id'].strip(),
                            submitted_timestamp=sub_dict['submitted_at'],
                            graded_timestamp=sub_dict['graded_at'],
                            score=sub_dict['score'],
                            transmitted=False
                        )
                        for sub_dict in sub_dicts
                    ]
                )
                LOGGER.info(f'Inserted {len(sub_dicts)} new Submission record(s) in the database')
            except Exception as e:
                LOGGER.error(e)
                LOGGER.error('Submissions bulk creation failed')

    def send_scores(self, subs_to_send: list[Submission]) -> None:
        """
        Sends scores in bulk for submissions with unique student_uniqname values and updates database when successful.

        :param subs_to_send: List of un-transmitted Submissions with non-repeating student_uniqname values.
        :type subs_to_send: List of Submission model instances
        :return: None
        :rtype: None
        """
        scores_to_send: list[dict[str, str]] = [sub.prepare_score() for sub in subs_to_send]
        payload: dict[str, Any] = {'putPlcExamScore': {'Student': scores_to_send}}
        json_payload: str = json.dumps(payload)
        LOGGER.debug(json_payload)

        extra_headers = [{'Content-Type': 'application/json'}]

        response: Response = self.api_handler.api_call(
            MPATHWAYS_URL,
            MPATHWAYS_SCOPE,
            'PUT',
            payload=json_payload,
            api_specific_headers=extra_headers
        )

        if not check_if_response_successful(response):
            LOGGER.error('There is a problem with the response; refer to the logs')
            LOGGER.info('No records will be updated in the database')
            return None

        resp_data: dict[str, Any] = json.loads(response.text)
        LOGGER.debug(resp_data)

        schema_name: str = 'putPlcExamScoreResponse'
        results: dict[str, Any] = resp_data[schema_name][schema_name]

        if results['BadCount'] > 0:
            LOGGER.warning(f"Discovered {results['BadCount']} record error(s): {results['Errors']}")

        # Hope this can be simplified in the future if API response data can be made to use consistent types
        if results['GoodCount'] > 1:
            success_uniqnames: list[str] = [success_dict['uniqname'] for success_dict in results['Success']]
        elif results['GoodCount'] == 1:
            success_uniqnames = [results['Success']['uniqname']]
        else:
            success_uniqnames = []

        if len(success_uniqnames) == 0:
            LOGGER.warning('No scores were transmitted successfully.')
        else:
            timestamp: datetime = datetime.now(tz=utc)

            subs_to_update: list[Submission] = []
            for sub in subs_to_send:
                if sub.student_uniqname in success_uniqnames:
                    sub.transmitted = True
                    sub.transmitted_timestamp = timestamp
                    subs_to_update.append(sub)
            Submission.objects.bulk_update(objs=subs_to_update, fields=['transmitted', 'transmitted_timestamp'])
            LOGGER.info(f'Transmitted {len(subs_to_update)} score(s) successfully and updated submission record(s).')
        return None

    def main(self) -> None:
        """
        High-level process method for class. Pulls Canvas data, sends data, and logs activity in the database.

        :return: None
        :rtype: None
        """
        # Fetch data from Canvas API and store as submission records in the database
        sub_dicts: list[dict[str, Any]] = self.get_sub_dicts_for_exam()
        if len(sub_dicts) > 0:
            self.create_sub_records(sub_dicts)

        # Find old and new submissions for exam to send to M-Pathways
        sub_to_transmit_qs: QuerySet = self.exam.submissions.filter(transmitted=False)
        subs_to_transmit: list[Submission] = list(sub_to_transmit_qs.all())

        # Identify old submissions for debugging purposes
        redo_subs: list[Submission] = list(sub_to_transmit_qs.filter(graded_timestamp__lt=self.sub_time_filter))
        if len(redo_subs) > 0:
            LOGGER.info(f'Will try to re-send {len(redo_subs)} previously un-transmitted submissions')
            LOGGER.debug(f'Previously un-transmitted submissions: {redo_subs}')

        # Identify and separate submissions to send with duplicate uniqnames
        freq_qs: QuerySet = sub_to_transmit_qs.values('student_uniqname').annotate(frequency=Count('student_uniqname'))
        dup_uniqnames: list[str] = [
            uniqname_dict['student_uniqname'] for uniqname_dict in list(freq_qs) if uniqname_dict['frequency'] > 1
        ]
        dup_uniqname_subs: list[Submission] = []
        regular_subs: list[Submission] = []
        for sub_to_transmit in subs_to_transmit:
            if sub_to_transmit.student_uniqname in dup_uniqnames:
                dup_uniqname_subs.append(sub_to_transmit)
            else:
                regular_subs.append(sub_to_transmit)

        # Send scores and update the database
        if len(regular_subs) > 0:
            # Send regular submissions in chunks of 100
            regular_sub_lists: list[list[Submission]] = chunk_list(regular_subs)
            for regular_sub_list in regular_sub_lists:
                self.send_scores(regular_sub_list)
        if len(dup_uniqname_subs) > 0:
            LOGGER.info('Found submissions to send with duplicate uniqnames; they will be sent individually')
            # Send each submission with a duplicate uniqname individually
            for dup_uniqname_sub in dup_uniqname_subs:
                self.send_scores([dup_uniqname_sub])

        return None
