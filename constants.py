# standard libraries
import os


# General
ISO8601_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

# Paths
ROOT_DIR: str = os.path.dirname(os.path.abspath(__file__))
API_FIXTURES_DIR = os.path.join(ROOT_DIR, 'test', 'api_fixtures')

# UM API Directory
CAMPUS_PREFIX = 'aa'

CANVAS_SCOPE_CAPS = 'CanvasReadOnly'
CANVAS_SCOPE = CANVAS_SCOPE_CAPS.lower()
CANVAS_URL_BEGIN = '/'.join([CAMPUS_PREFIX, CANVAS_SCOPE_CAPS])

MPATHWAYS_SCOPE_CAPS = 'SpanishPlacementScores'
MPATHWAYS_SCOPE = MPATHWAYS_SCOPE_CAPS.lower()
MPATHWAYS_URL = '/'.join([CAMPUS_PREFIX, MPATHWAYS_SCOPE_CAPS, 'Scores'])

SCORE_RANDOMIZER_FOR_TEST = 'test_enable_score_randomizer'
TEST = 'test'
SMPT_DEBUG = 'smpt_debug'
SMPT_FROM = 'smpt_from'
SMPT_TO = 'smpt_to'
SMPT_HOST = 'smpt_host'
SMPT_PORT = 'smpt_port'
