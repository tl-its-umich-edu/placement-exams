# standard libraries
import os


# General
ISO8601_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

# Paths
ROOT_DIR: str = os.path.dirname(os.path.abspath(__file__))
TEST_DIR: str = os.path.join(ROOT_DIR, 'test')
API_FIXTURES_DIR = os.path.join(TEST_DIR, 'api_fixtures')
SNAPSHOTS_DIR = os.path.join(TEST_DIR, 'snapshots')

# UM API Directory
CAMPUS_PREFIX = 'aa'

CANVAS_SCOPE_CAPS = 'CanvasReadOnly'
CANVAS_SCOPE = CANVAS_SCOPE_CAPS.lower()
CANVAS_URL_BEGIN = '/'.join([CAMPUS_PREFIX, CANVAS_SCOPE_CAPS])

MPATHWAYS_SCOPE_CAPS = 'PlacementScores'
MPATHWAYS_SCOPE = MPATHWAYS_SCOPE_CAPS.lower()
MPATHWAYS_URL = '/'.join([CAMPUS_PREFIX, MPATHWAYS_SCOPE_CAPS, 'Scores'])
