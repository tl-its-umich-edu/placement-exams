# standard libraries
import logging, os, sys
from datetime import datetime
from typing import List

# third-party libraries
from autologging import logged
from django.core.wsgi import get_wsgi_application
from dotenv import load_dotenv
from umich_api.api_utils import ApiUtil

# local libraries
# from exam_date.stored_date import AssignmentLatestSubmittedDate
# from scores_orchestration.orchestration import SpanishScoresOrchestration
# from spe_utils import constants
# from spe_report.summary import SPESummaryReport


# Initialize globals and environment

# Logging will be configured in config/settings.py
LOGGER = logging.getLogger(__name__)

ROOT_DIR: str = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR: str = os.getenv('ENV_DIR', os.path.join('config', 'secrets'))
ENV_PATH: str = os.path.join(ROOT_DIR, CONFIG_DIR, os.getenv('ENV_FILE', '.env'))

load_dotenv(dotenv_path=ENV_PATH, verbose=True)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pe.settings')

# settings.py has to be run before using pe/models.py (which get_wsgi_application uses), and
# load_dotenv has to be run before settings.py
try:
    application = get_wsgi_application()
    from pe.models import Exam, Report
except Exception as e:
    LOGGER.error(e)
    LOGGER.error('Failed to load Django application; the program will exit')
    sys.exit(1)

try:
    API_UTIL: ApiUtil = ApiUtil(
        os.getenv('API_DIR_URL', ''),
        os.getenv('API_DIR_CLIENT_ID', ''),
        os.getenv('API_DIR_SECRET', ''),
        os.path.join(ROOT_DIR, 'config', 'apis.json')
    )
except Exception as e:
    LOGGER.error(e)
    LOGGER.error('Failed to connect to Canvas UM API Directory; the program will exit.')
    sys.exit(1)


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
