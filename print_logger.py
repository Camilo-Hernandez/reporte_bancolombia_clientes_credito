import logging
import sys


class PrintLogger:
    """
    Custom stream handler to redirect print() statements to a logger.
    """

    def __init__(self, logger, level=logging.INFO):
        self.logger = logger
        self.level = level

    def write(self, message):
        # Avoid logging empty lines
        if message.strip():
            self.logger.log(self.level, message.strip())

    def flush(self):
        pass  # Required for compatibility with sys.stdout


def setup_logger():
    """
    Configures the logger for the project.
    """
    logger = logging.getLogger("project_logger")
    logger.setLevel(logging.DEBUG)

    # Create a console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    # Create a file handler
    file_handler = logging.FileHandler("project.log", mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    # Define a logging format
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
