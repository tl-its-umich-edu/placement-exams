from autologging import logged, traced
from pathlib import Path
from datetime import datetime


@logged
@traced
class AssignmentLatestSubmittedDate():
    def __init__(self, path: str, file_name: str):
        self.path = path
        self.file_name = file_name

    def _create_directory_if_not_exit(self):
        """
        creates a directory if doesn't exit with permission 0o777
        raises exception in case of anamolies
        """
        try:
            if not Path(self.path).exists():
                self.__log.info(f"creating the directory at {self.path}")
                Path(self.path).mkdir(parents=True, exist_ok=True)
        except (OSError, Exception) as e:
            raise e


    def get_assign_submitted_date(self) -> str:
        """
        creating a directory/file if not available that holds the latest score date. It writes the current UTC date
        if not provided so that initial run will end up happening. Raises exception when creating a directory and
        reading the content of the persisted.txt
        :return: latest_score_timestamp
        """
        try:
            self._create_directory_if_not_exit()
        except (OSError, Exception) as e:
            self.__log.error(f"error in creating a directory due to {e}")
            raise e
        try:
            path_to_persisted_file: str = self.path + '/'+self.file_name
            self.__log.info(f"file to opened {path_to_persisted_file}")

            if not Path(path_to_persisted_file).exists():
                self.__log.info(f"The file {self.file_name} doesn't exist this happen during the very first run")
                latest_score_timestamp = self._create_write_persisted_file(path_to_persisted_file)
                return latest_score_timestamp
            return self._read_persisted_file(path_to_persisted_file)

        except (OSError, IOError, Exception) as e:
            self.__log.error(f"error while reading the file {self.file_name} due to {e}")
            raise e

    def _create_write_persisted_file(self, path_to_persisted_file: str) -> str:
        try:
            with open(path_to_persisted_file, 'w+') as f:
                latest_score_timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                self.__log.info(f"""writing to file {self.file_name} the latest test taken date in
                                UTC with current timestamp {latest_score_timestamp}""")
                f.write(latest_score_timestamp)
                return latest_score_timestamp
        except (OSError, IOError, Exception) as e:
            self.__log.error(f"failed do read the file {path_to_persisted_file} due to {e}")
            raise e

    def _read_persisted_file(self, path_to_persisted_file: str) -> str:
        try:
            with open(path_to_persisted_file) as f:
                latest_exam_date: str = f.read()
                self.__log.info(f"""reading from to file {self.file_name} the latest test taken date in
                                UTC with current timestamp {latest_exam_date}""")
                return latest_exam_date.strip()
        except (OSError, IOError, Exception) as e:
            self.__log.error(f"failed do read the file {path_to_persisted_file} due to {e}")
            raise e
