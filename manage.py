# standard libraries
import logging, os, sys

# third-party libraries
from dotenv import load_dotenv


ENV_PATH = os.path.join(os.getenv('ENV_DIR', os.path.join('config', 'secrets')), os.getenv('ENV_FILE', '.env'))
load_dotenv(dotenv_path=ENV_PATH, verbose=True)

LOGGER = logging.getLogger(__name__)

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        LOGGER.error('django.core.management not found')
    execute_from_command_line(sys.argv)
