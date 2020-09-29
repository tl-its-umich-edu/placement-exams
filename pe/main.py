# standard libraries
import logging
from logging import Logger
from datetime import datetime, timedelta
from typing import Dict, List

# third-party libraries
from django.utils.timezone import utc
from umich_api.api_utils import ApiUtil

# local libraries
from pe.models import Exam, Report
from pe.orchestration import ScoresOrchestration
from pe.reporter import Reporter


LOGGER: Logger = logging.getLogger(__name__)


def main(api_util: ApiUtil) -> None:
    """
    Runs the highest-level application process, coordinating the use of ScoresOrchestration and Reporter
    classes and the transfer of data between them.

    :param api_util: Instance of ApiUtil for making API calls
    :type api_util: ApiUtil
    :return: None
    :rtype: None
    """
    start_time: datetime = datetime.now(tz=utc)
    LOGGER.info(f'Starting new run at {start_time}')

    reports: List[Report] = list(Report.objects.all())
    LOGGER.debug(reports)

    exams: List[Exam] = list(Exam.objects.all())
    LOGGER.debug(exams)

    for report in reports:
        reporter: Reporter = Reporter(report)
        for exam in report.exams.all():
            LOGGER.info(f'Processing Exam: {exam.name}')
            exam_start_time = datetime.now(tz=utc)
            exam_orca: ScoresOrchestration = ScoresOrchestration(api_util, exam)
            exam_orca.main()
            exam_end_time = datetime.now(tz=utc)
            metadata: Dict[str, datetime] = {
                'start_time': exam_start_time,
                'end_time': exam_end_time,
                'sub_time_filter': exam_orca.sub_time_filter
            }
            reporter.exams_time_metadata[exam.id] = metadata
        reporter.prepare_context()
        LOGGER.info(f'Sending {report.name} report email to {report.contact}')
        reporter.send_email()

    end_time: datetime = datetime.now(tz=utc)
    delta: timedelta = end_time - start_time

    LOGGER.info(f'The run ended at {end_time}')
    LOGGER.info(f'Duration of run: {delta}')
