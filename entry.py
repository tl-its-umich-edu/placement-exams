import logging
import os
import sys

from autologging import logged
from dotenv import load_dotenv
from datetime import datetime

from exam_date.stored_date import AssignmentLatestSubmittedDate
from scores_orchestration.orchestration import SpanishScoresOrchestration
from spe_utils import constants
from spe_report.summary import SPESummaryReport

load_dotenv(dotenv_path=os.path.dirname(os.path.abspath(__file__)) + "/.env")


@logged
def set_up_logging():
    level = constants.LOGGING_LEVEL
    log_level = os.getenv(level)
    if log_level:
        logging.basicConfig(level=log_level, stream=sys.stdout,
                            format="%(asctime)s - %(levelname)s -  %(name)s - %(funcName)s - %(message)s")


@logged
def main():
    start_time: datetime = datetime.now()
    set_up_logging()
    logging.info(f"Starting of new cron run at {start_time} ")

    path: str = os.getenv(constants.PERSISTENT_PATH)
    file_name: str = os.getenv(constants.FILE_NAME)
    query_date_holder: AssignmentLatestSubmittedDate = AssignmentLatestSubmittedDate(path, file_name)

    try:
        stored_submission_date: str = query_date_holder.get_assign_submitted_date()
    except (OSError, IOError, Exception) as e:
        logging.error(f"error retrieving the latest assignment submitted date due to {e}")
        return

    spe_report: SPESummaryReport = SPESummaryReport()
    score_handler: SpanishScoresOrchestration = SpanishScoresOrchestration(stored_submission_date, spe_report)
    next_query_date: str = score_handler.orchestrator()
    if next_query_date:
        try:
            query_date_holder.store_next_query_date(next_query_date)
            spe_report.next_stored_persisted_date = next_query_date
        except (OSError, IOError, Exception) as e:
            logging.error(f"""error storing the latest assignment submitted date due to {e} 
                        stored date in persisted storage is {stored_submission_date}""")
            spe_report.next_stored_persisted_date = stored_submission_date
    else:
        logging.info(f"No next Query date to update either no new scores or error in sending first score")
        spe_report.next_stored_persisted_date = stored_submission_date

    end_time: datetime = datetime.now()
    elapsed_time: datetime = end_time - start_time

    spe_report.start_time = start_time
    spe_report.end_time = end_time
    spe_report.elapsed_time = elapsed_time

    spe_report.send_email()

    logging.info(f"ending of the cron run at {end_time} ")
    logging.info(f"This cron run took about {elapsed_time}")



if __name__ == '__main__':
    main()
