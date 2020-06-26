# standard libraries
import os

# General
ISO8601_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

# Paths
ROOT_DIR: str = os.path.dirname(os.path.abspath(__file__))
API_FIXTURES_DIR = os.path.join(ROOT_DIR, 'test', 'api_fixtures')

# UM API Directory
CANVAS_SCOPE = 'canvasreadonly'
MPATHWAYS_SCOPE = 'spanishplacementscores'

SCORE_RANDOMIZER_FOR_TEST = 'test_enable_score_randomizer'
TEST = 'test'
SMPT_DEBUG = 'smpt_debug'
SMPT_FROM = 'smpt_from'
SMPT_TO = 'smpt_to'
SMPT_HOST = 'smpt_host'
SMPT_PORT = 'smpt_port'
