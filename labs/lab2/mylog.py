import logging
import os

class ColoredFormatter(logging.Formatter):
    COLORS = {
        'time': '\033[34m',      # Blue
        'process': '\033[36m',   # Cyan
        'filename': '\033[35m',  # Magenta
        'info': '\033[32m',      # Green
        'warning': '\033[33m',   # Yellow
        'error': '\033[31m',     # Red
        'critical': '\033[41m',  # Red background
        'reset': '\033[0m',      # Reset to default color
    }

    def format(self, record):
        level_color = self.COLORS.get(record.levelname.lower(), self.COLORS['reset'])
        time_color = self.COLORS.get('time', self.COLORS['reset'])
        process_color = self.COLORS.get('process', self.COLORS['reset'])
        filename_color = self.COLORS.get('filename', self.COLORS['reset'])
        reset_color = self.COLORS['reset']

        log_message = super().format(record)
        log_message = log_message.replace(
            record.asctime, f"{time_color}{record.asctime}{reset_color}"
        )
        log_message = log_message.replace(
            f"{record.process}", f"{process_color}{record.process}{reset_color}"
        )
        log_message = log_message.replace(
            record.levelname, f"{level_color}{record.levelname}{reset_color}"
        )
        log_message = log_message.replace(
            record.filename, f"{filename_color}{record.filename}{reset_color}"
        )
        log_message = log_message.replace(
            record.threadName, f"{level_color}{record.threadName}{reset_color}"
        )
        return log_message

class Logger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance.setup_logging()
        return cls._instance

    def setup_logging(self, log_level=logging.INFO, log_file="app.log"):
        self.logger = logging.getLogger()
        self.logger.setLevel(log_level)

        console_handler = logging.StreamHandler()
        console_formatter = ColoredFormatter(
            '%(asctime)s - %(process)d - %(threadName)s - %(filename)s:%(lineno)d- %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)

        file_handler = logging.FileHandler(log_file, mode='w')
        file_formatter = logging.Formatter(
            '%(asctime)s - %(process)d - %(threadName)s - %(filename)s:%(lineno)d- %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)

        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    def get_logger(self):
        return self.logger

