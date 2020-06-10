# standard libraries
import json, logging, os, sys
from json.decoder import JSONDecodeError
from logging import Logger
from typing import Dict, Union

# third-party libraries
from dotenv import load_dotenv
from jsonschema import validate
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

# This file is committed to the repository and will always be present
with open(os.path.join(ROOT_DIR, 'config', 'fixture_schema.json')) as fixture_schema_file:
    FIXTURES_SCHEMA: Dict = json.loads(fixture_schema_file.read())

config_problem: bool = False

# Load fixture file
FIXTURES: Union[Dict, None] = None
try:
    fixtures_path: str = os.path.join(CONFIG_DIR, ENV.get('FIXTURES_NAME', 'fixtures.json'))
    with open(fixtures_path, 'r', encoding='utf8') as fixtures_file:
        fixtures_str: str = fixtures_file.read()

    try:
        FIXTURES = json.loads(fixtures_str)
    except JSONDecodeError:
        LOGGER.error(f'Did not find valid JSON in {fixtures_path}')
        config_problem = True

except FileNotFoundError:
    LOGGER.error(f'Failed to find fixtures file at {fixtures_path}')
    config_problem = True
    

if FIXTURES is not None:
    # Validate FIXTURES using FIXTURES_SCHEMA
    try:
        validate(instance=FIXTURES, schema=FIXTURES_SCHEMA)
        LOGGER.info('FIXTURES is valid')
    except Exception as e:
        LOGGER.error(e)
        LOGGER.error('FIXTURES is invalid')
        config_problem = True

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
