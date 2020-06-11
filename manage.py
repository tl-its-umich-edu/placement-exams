import logging, os, sys


LOGGER = logging.getLogger(__name__)

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        LOGGER.error('django.core.management not found')
    execute_from_command_line(sys.argv)
