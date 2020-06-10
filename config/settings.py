# standard libraries
import os
from typing import Dict, List

# third-party libraries
from dotenv import load_dotenv


# This is loaded separately from configure so that code doesn't run multiple times
# when manage.py is used in start.sh.
ROOT_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR: str = os.path.join(ROOT_DIR, 'config', 'secrets')
load_dotenv(dotenv_path=os.path.join(CONFIG_DIR, os.getenv('ENV_FILE', '.env')))

# Django settings

BASE_DIR: str = ROOT_DIR

DATABASES: Dict[str, Dict[str, str]] = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('NAME', 'placement_exams_local'),
        'USER': os.getenv('USER', 'pe_user'),
        'PASSWORD': os.getenv('PASSWORD', 'pe_pw'),
        'HOST': os.getenv('HOST', 'placement_exams_mysql'),
        'PORT': os.getenv('PORT', '3306')
    }
}

INSTALLED_APPS: List[str] = [
    'db'
]

SECRET_KEY: str = os.getenv('SECRET_KEY', '-- A SECRET KEY --')
