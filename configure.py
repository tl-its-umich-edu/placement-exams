# standard libraries
import logging, os, sys
from logging import Logger
from typing import Dict

# third-party libraries
from dotenv import load_dotenv
from umich_api.api_utils import ApiUtil


LOGGER: Logger = logging.getLogger(__name__)

# Set up path variables
ROOT_DIR: str = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR: str = os.path.join(ROOT_DIR, os.getenv('ENV_DIR', os.path.join('config', 'secrets')))
CONFIG_PATH: str = os.path.join(CONFIG_DIR, os.getenv('ENV_FILE', 'env.json'))
API_CONFIG_PATH: str = os.path.join(ROOT_DIR, 'config', 'apis.json')

load_dotenv(dotenv_path=os.path.join(CONFIG_DIR, os.getenv('ENV_FILE', '.env')))
ENV: Dict = dict(os.environ)

log_level: str = ENV.get('LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=log_level,
    stream=sys.stdout,
    format='%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s'
)

config_problem: bool = False

# Set up ApiUtil
try:
    API_UTIL: ApiUtil = ApiUtil(
        os.getenv('API_DIR_URL', ''),
        os.getenv('API_DIR_CLIENT_ID', ''),
        os.getenv('API_DIR_SECRET', ''),
        API_CONFIG_PATH
    )
except Exception as e:
    LOGGER.error(e)
    LOGGER.error('Failed to connect to Canvas UM API Directory; the program will exit.')
    config_problem = True

if config_problem:
    LOGGER.error('One or more configuration problems were encountered; the program will exit')
    sys.exit(1)
else:
    LOGGER.info('Configuration files were successfully loaded; the program will continue')
