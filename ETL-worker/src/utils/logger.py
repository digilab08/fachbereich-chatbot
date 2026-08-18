import logging
import os
from typing import Union
from dotenv import load_dotenv

# Load environment variables once when the module is imported
load_dotenv()

def _get_log_level(default_level: str = "INFO") -> int:
    """Retrieve and validate the numeric log level from environment variables.

    :param default_level: Fallback level string if LOG_LEVEL is invalid or missing.
    :type default_level: str
    :return: Numeric logging level constant from the logging module.
    :rtype: int
    """
    level_str: str = os.getenv("LOG_LEVEL", default_level).strip().upper()
    numeric_level: Union[int, None] = getattr(logging, level_str, None)
    
    if not isinstance(numeric_level, int):
        # Fallback to default if the string doesn't match a valid logging level
        return getattr(logging, default_level, logging.INFO)
        
    return numeric_level

def get_logger(module_name: str) -> logging.Logger:
    """Create and configure a standardized logger instance.

    This function ensures that the logger is configured with the correct format
    and level based on the .env file. It also prevents duplicate logs by checking
    if handlers are already attached.

    :param module_name: The name of the module requesting the logger (usually __name__).
    :type module_name: str
    :return: A fully configured logger instance.
    :rtype: logging.Logger
    """
    logger: logging.Logger = logging.getLogger(module_name)
    
    # Check if handlers already exist to prevent duplicate log entries
    if not logger.hasHandlers():
        log_level: int = _get_log_level()
        logger.setLevel(log_level)
        
        # Configure console output
        console_handler: logging.StreamHandler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        
        # Define the log message format
        formatter: logging.Formatter = logging.Formatter(
            fmt="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(formatter)
        
        # Attach the handler to the logger
        logger.addHandler(console_handler)
        
        # Prevent log messages from propagating up to the root logger
        # to avoid double output if the root logger is also configured
        logger.propagate = False
        
    return logger