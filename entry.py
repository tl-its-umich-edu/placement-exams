import logging, sys
from typing import Any, Union

from autologging import logged
from exam_date.stored_date import AssignmentLatestSubmittedDate
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
    more_path: str = os.path.dirname(os.path.abspath(__file__)) + path
    read_date: AssignmentLatestSubmittedDate = AssignmentLatestSubmittedDate(more_path, file_name)
    read_date.get_assign_submitted_date()


if __name__ == '__main__':
    main()
