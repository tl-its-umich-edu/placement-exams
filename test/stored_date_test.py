import logging
import os
import shutil
import unittest
from autologging import logged
from datetime import datetime
from exam_date.stored_date import AssignmentLatestSubmittedDate

logging.basicConfig(level=os.getenv("log_level", "DEBUG"))


@logged
class TestSPEProcess(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.__log.info("you got into the testing zone")
        this_dir = os.path.dirname(os.path.abspath(__file__))
        self.persisted_dir: str = '/tmp/' + 'PERSIST'
        self.file_name: str = 'test_persisted.txt'

    def _check_date_format(self, utc_date: str):
        try:
            datetime.strptime(utc_date, '%Y-%m-%dT%H:%M:%SZ')
            return "Date is in correct format"
        except ValueError:
            raise ValueError("Incorrect data format")

    def test_dir_and_file_created(self):
        '''
        this is testing if the persisted.txt dir and file created and see if data is in the format
        %Y-%m-%dT%H:%M:%SZ. deleting the dir only if exist for making the test case still relevant
        for subsequent runs
        :return:
        '''
        if os.path.exists(self.persisted_dir):
            shutil.rmtree(self.persisted_dir)
        self.assertEqual(False, os.path.exists(self.persisted_dir))
        date_holder = AssignmentLatestSubmittedDate(self.persisted_dir, self.file_name)
        latest_test_taken_date = date_holder.get_assign_submitted_date()
        self.assertEqual("Date is in correct format", self._check_date_format(latest_test_taken_date))

    def test_write_to_file(self):
        """
        testing persisted.txt return the utc time stamp
        :return:
        """

        with open(self.persisted_dir+'/'+self.file_name, 'w') as f:
            f.write('anything but time')
        date_holder = AssignmentLatestSubmittedDate(self.persisted_dir, self.file_name)
        date = date_holder.get_assign_submitted_date()
        self.assertEqual('anything but time', date)


