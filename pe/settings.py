# standard libraries
import os
from typing import Any

# local libraries
from constants import ROOT_DIR


# Django settings

BASE_DIR: str = ROOT_DIR

CONFIG_DIR: str = os.path.join(BASE_DIR, os.getenv('ENV_DIR', os.path.join('config', 'secrets')))

DATABASES: dict[str, dict[str, Any]] = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME', 'placement_exams_local'),
        'USER': os.getenv('DB_USER', 'pe_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'pe_pw'),
        'HOST': os.getenv('DB_HOST', 'placement_exams_mysql'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'OPTIONS': {'charset': 'utf8mb4'},
        'TEST': {
            'CHARSET': 'utf8mb4',
            'COLLATION': 'utf8mb4_unicode_ci'
        }
    }
}

DATETIME_FORMAT: str = "N j, Y g:i:s a"

if bool(int(os.getenv('EMAIL_DEBUG', '1'))):
    EMAIL_BACKEND: str = 'django.core.mail.backends.console.EmailBackend'

EMAIL_HOST: str = os.getenv('SMTP_HOST', '')
EMAIL_PORT: int = int(os.getenv('SMTP_PORT', 0))
EMAIL_USE_TLS: bool = True

FIXTURE_DIRS: list[str] = [
    CONFIG_DIR,
    os.path.join(BASE_DIR, 'test', 'fixtures')
]

LOGGING: dict[str, Any] = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        }
    },
    'root': {
        'handlers': ['console'],
        'level': os.getenv('LOG_LEVEL', 'INFO')
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'propagate': False
        }
    }
}

INSTALLED_APPS: list[str] = [
    'pe'
]

SECRET_KEY: str = os.getenv('SECRET_KEY', '-- A SECRET KEY --')

TEMPLATES: list[dict[str, Any]] = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],
        'APP_DIRS': True
    }
]

TIME_ZONE: str = os.getenv('TIME_ZONE', 'America/Detroit')
USE_TZ: bool = True
