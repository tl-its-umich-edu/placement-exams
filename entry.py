# standard libraries
import logging, os, sys
from logging import Logger
from datetime import datetime, timedelta
from typing import Dict, List

# third-party libraries
from django.core.wsgi import get_wsgi_application
from django.utils.timezone import utc
from dotenv import load_dotenv
from umich_api.api_utils import ApiUtil

# local libraries
from constants import ROOT_DIR


# Initialize globals and environment

# Logging will be configured in config/settings.py
LOGGER: Logger = logging.getLogger(__name__)

CONFIG_DIR: str = os.getenv('ENV_DIR', os.path.join('config', 'secrets'))
ENV_PATH: str = os.path.join(ROOT_DIR, CONFIG_DIR, os.getenv('ENV_FILE', '.env'))

load_dotenv(dotenv_path=ENV_PATH, verbose=True)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pe.settings')

# settings.py has to be run before using pe/models.py (which get_wsgi_application uses), and
# load_dotenv has to be run before settings.py
try:
    application = get_wsgi_application()
    from pe.models import Exam, Report
    from pe.orchestration import ScoresOrchestration
    from pe.reporter import Reporter
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


def main() -> None:
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
            exam_orca: ScoresOrchestration = ScoresOrchestration(API_UTIL, exam)
            exam_orca.main()
            exam_end_time = datetime.now(tz=utc)
            metadata: Dict[str, datetime] = {
                'start_time': exam_start_time,
                'end_time': exam_end_time,
                'datetime_filter': exam_orca.sub_time_filter
            }
            reporter.exams_time_metadata[exam.id] = metadata
        reporter.prepare_context()
        LOGGER.info(f'Sending email to {report.contact}')
        reporter.send_email()

    end_time: datetime = datetime.now(tz=utc)
    delta: timedelta = end_time - start_time

    LOGGER.info(f'The run ended at {end_time}')
    LOGGER.info(f'Duration of run: {delta}')


if __name__ == '__main__':
    main()
