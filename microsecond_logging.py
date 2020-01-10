"""
Provides a logging function with microsecond resolution

Based on these StackOverflow answers:

    https://stackoverflow.com/a/6290946/3657941
    https://stackoverflow.com/a/13638084/3657941

"""

import logging
import logging.handlers
import datetime

# DEBUG is 10 and NOTSET is 0 so we put TRACE between them
TRACE = logging.DEBUG - 5


class MicrosecondFormatter(logging.Formatter):
    """
    Class for creating a microsecond resolution format string
    """
    converter = datetime.datetime.fromtimestamp

    def formatTime(self, record, datefmt=None):
        convert = self.converter(record.created)
        if datefmt:
            result = convert.strftime(datefmt)
        else:
            result = convert.strftime("%Y-%m-%d %H:%M:%S")
            result = "%s.%03d" % (result, record.msecs)
        return result


def trace(self, msg, *args, **kwargs):
    """
    Add trace logging level
    """
    if self.isEnabledFor(TRACE):
        self._log(TRACE, msg, args, **kwargs)


logging.addLevelName(TRACE, 'TRACING')
logging.Logger.trace = trace


def getLogger(name, log_to_console=True, log_file_name=None, bare=False):
    """
    Return a logger with the desired name using the millisecond formatter
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        if bare:
            fmt = '\
%(asctime)s: %(levelname)-7s: %(message)s'
        else:
            fmt = '\
%(asctime)s: %(filename)s: %(lineno)5d: %(levelname)-7s: %(message)s'
        datefmt = '%Y-%m-%d %H:%M:%S.%f'
        # Prevent logging from propagating to the root logger
        logger.propagate = 0
        # Create the formatter
        formatter = MicrosecondFormatter(fmt=fmt, datefmt=datefmt)
        # If we want to log to the console
        if log_to_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        # If we want to log to a file
        if log_file_name is not None:
            file_handler = logging.handlers.WatchedFileHandler(log_file_name)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
    return logger


# Import constants and methods needed by users of this module.
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL, basicConfig
