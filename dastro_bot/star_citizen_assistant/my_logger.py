import logging
from logging.handlers import RotatingFileHandler
import os
import sys


class DuplicateFilter(logging.Filter):
    """ a filter to suppress repeating log messages """
    def __init__(self):
        logging.Filter.__init__(self)
        self.last_log = None

    def filter(self, record):
        current_log = record.msg
        if current_log != self.last_log:
            self.last_log = current_log
            return True
        return False


class MyLogger(logging.Logger):
    """
    Preconfigured logger class with parameters:
    :param log_file_name: name of log file to write to
    :param log_level:
    :param log_file_size_limit_bytes: if the limit exceeds file will be backed up and cleared
    :return: preconfigured logger object
    """
    def __init__(self, log_file_name="logfile.log", log_level=logging.DEBUG, logger_name='my logger',
                 log_file_size_limit_bytes=1024*1024, log_file_dir="logs", use_script_dir=False, prefix=""):

        logging.Logger.__init__(self, logger_name)

        logs_formatter = logging.Formatter(f'%(asctime)s [%(levelname)s]{prefix} %(message)s')
        self.addFilter(DuplicateFilter())
        self.setLevel(log_level)

        if log_file_name:
            self.log_dir_path = self._get_log_dir(log_file_dir, use_script_dir)
            self.log_file_path = os.path.join(self.log_dir_path, log_file_name)
            if not os.path.isdir(self.log_dir_path):
                os.mkdir(self.log_dir_path)
            self.log_file = RotatingFileHandler(self.log_file_path, maxBytes=log_file_size_limit_bytes, backupCount=5)
            self.log_file.setFormatter(logs_formatter)
            self.addHandler(self.log_file)

    @staticmethod
    def _get_log_dir(log_file_dir, use_script_dir):
        if use_script_dir:
            base_dir = os.path.dirname(os.path.realpath(__file__))
            return os.path.join(base_dir, log_file_dir)
        else:
            return log_file_dir

    def write(self, message):
        """
        Write method to provide a way of redirecting stdout.
        """
        if "error" in message.lower():
            self.error(message)
        else:
            self.debug(message)

    def flush(self):
        """
        Flush method to provide a way of redirecting stdout.
        """
        self.error(sys.stderr)
