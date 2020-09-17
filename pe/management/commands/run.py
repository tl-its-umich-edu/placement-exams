# standard libraries
import logging, os, sys
from logging import Logger

# third-party libraries
from django.core.management.base import BaseCommand
from umich_api.api_utils import ApiUtil

# local libraries
from pe.main import main
from constants import ROOT_DIR


LOGGER: Logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Django management command used for launching the process defined in the main module.
    """

    def handle(self, *args, **options) -> None:
        """
        Entrypoint method required by BaseCommand class (see Django docs).
        Checks whether the ApiUtil instance is properly configured, invoking the main function if so
        and exiting if not.
        """
        try:
            api_util: ApiUtil = ApiUtil(
                os.getenv('API_DIR_URL', ''),
                os.getenv('API_DIR_CLIENT_ID', ''),
                os.getenv('API_DIR_SECRET', ''),
                os.path.join(ROOT_DIR, 'config', 'apis.json')
            )
        except Exception as e:
            LOGGER.error(e)
            LOGGER.error('api_util was improperly configured; the program will exit.')
            sys.exit(1)

        main(api_util)
