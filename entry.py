import logging, sys
from typing import Optional, Any

from autologging import logged

from exam_date.stored_date import AssignmentLatestSubmittedDate
from scores_orchestration.orchestration import SpanishScoresOrchestration
from spe_utils import utils
import os

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.dirname(os.path.abspath(__file__)) + "/.env")


@logged
def set_up_logging():
    level = utils.LOGGING_LEVEL
    log_level = os.getenv(level)
    if log_level:
        logging.basicConfig(level=log_level, stream=sys.stdout,
                            format="%(asctime)s - %(levelname)s -  %(name)s - %(funcName)s - %(message)s")


@logged
def main():
    set_up_logging()

    path: str = os.getenv(utils.PERSISTENT_PATH)
    file_name: str = os.getenv(utils.FILE_NAME)
    query_date_holder: AssignmentLatestSubmittedDate = AssignmentLatestSubmittedDate(path, file_name)

    try:
        stored_submission_date: str = query_date_holder.get_assign_submitted_date()
    except (OSError, IOError, Exception) as e:
        logging.error(f"error retrieving the latest assignment submitted date due to {e}")
        return

    score_handler: SpanishScoresOrchestration = SpanishScoresOrchestration(stored_submission_date)
    next_query_date: str = score_handler.orchestrator()
    if not next_query_date:
        logging.info(f"There is no new scores yet for date {stored_submission_date}")
        return

    query_date_holder.store_next_query_date(next_query_date)



if __name__ == '__main__':
    main()
