# standard libraries
import logging, os
from unittest.mock import patch

# third-party libraries
from django.core.management import call_command
from django.test import TestCase

# local libraries
from constants import ROOT_DIR


LOGGER = logging.getLogger(__name__)


class RunCommandTestCase(TestCase):

    def test_handle_with_properly_configured_api_util(self):
        """
        handle launches the pe.main.main function if ApiUtil is properly configured.
        """
        # Patch main so it isn't invoked
        with patch('pe.main.main', autospec=True) as mock_main:
            call_command('run')

        mock_main.assert_called()

    def test_handle_with_improperly_configured_api_util(self):
        """
        handle exits without calling pe.main.main if ApiUtil is improperly configured because
        the apis.json configuration file was not found at the specified path.
        """
        fake_config_path: str = os.path.join(ROOT_DIR, 'fake_dir_name', 'apis.json')
        with patch('constants.API_CONFIG_PATH', fake_config_path):
            # Patch main as a precaution so it isn't invoked
            with patch('pe.main.main', autospec=True) as mock_main:
                try:
                    call_command('run')
                except SystemExit:
                    LOGGER.info('SystemExit exception caught to enable subsequent test assertion.')

        mock_main.assert_not_called()
