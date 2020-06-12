# standard libraries
import logging
# import os
from datetime import datetime
# from typing import Dict
from typing import List

# third-party libraries
from autologging import logged
from django.core.wsgi import get_wsgi_application

# local libraries
import configure
# from exam_date.stored_date import AssignmentLatestSubmittedDate
# from scores_orchestration.orchestration import SpanishScoresOrchestration
# from spe_utils import constants
# from spe_report.summary import SPESummaryReport

# settings.py has to be loaded prior to using pe/models.py
application = get_wsgi_application()
from pe.models import Exam, Report


@logged
def main():
    start_time: datetime = datetime.now()
    logging.info(f'Starting new run at {start_time}')

    reports: List[Report] = list(Report.objects.all())
    logging.info(reports)

    exams: List[Exam] = list(Exam.objects.all())
    logging.info(exams)

    # path: str = os.getenv(constants.PERSISTENT_PATH)
    # file_name: str = os.getenv(constants.FILE_NAME)
    # query_date_holder: AssignmentLatestSubmittedDate = AssignmentLatestSubmittedDate(path, file_name)

    # try:
    #     stored_submission_date: Dict[str, str] = query_date_holder.get_assign_submitted_date()
    # except (OSError, IOError, Exception) as e:
    #     logging.error(f"error retrieving the latest assignment submitted date due to {e}")
    #     return

    # spe_report: SPESummaryReport = SPESummaryReport()
    # score_handler: SpanishScoresOrchestration = SpanishScoresOrchestration(stored_submission_date, spe_report)
    # next_query_date: Dict[str, str] = score_handler.orchestrator()
    # if next_query_date:
    #     try:
    #         # sorting the dict so that it always be in format {'place':2019-09-12T14:04:42Z, 'val':2019-09-15T14:04:42Z}
    #         sorted_next_query_date = dict(sorted(next_query_date.items()))
    #         query_date_holder.store_next_query_date(sorted_next_query_date)
    #         spe_report.next_stored_persisted_date = sorted_next_query_date
    #     except (OSError, IOError, Exception) as e:
    #         logging.error(f"""error storing the latest assignment submitted date due to {e} 
    #                     stored date in persisted storage is {stored_submission_date}""")
    #         spe_report.next_stored_persisted_date = stored_submission_date
    # else:
    #     logging.info(f"No next Query date to update either no new scores or error in sending first score")
    #     spe_report.next_stored_persisted_date = stored_submission_date

    end_time: datetime = datetime.now()
    delta: datetime = end_time - start_time

    # spe_report.start_time = start_time
    # spe_report.end_time = end_time
    # spe_report.elapsed_time = delta

    # if spe_report.is_any_scores_received():
    #     logging.info('Sending Email....')
    #     spe_report.send_email()
    # else:
    #     logging.info('Not Sending Email since no scores received')

    logging.info(f'The run ended at {end_time}')
    logging.info(f'Duration of run: {delta}')


if __name__ == '__main__':
    main()
