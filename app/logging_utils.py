import json
import logging
import logging.config
from pythonjsonlogger import jsonlogger
from enum import Enum

logger = logging.getLogger("wsgi")

def configure_json_logging():
    """Configure JSON logging for better observability in production"""
    logHandler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter()
    logHandler.setFormatter(formatter)
    logger = logging.getLogger("app")
    logger.addHandler(logHandler)
    logger.setLevel(logging.INFO)

class LogLevel(Enum):
    DEBUG="DEBUG"
    INFO="INFO"
    WARNING="WARNING"
    ERROR="ERROR"
    CRITICAL="CRITICAL"
    EXCEPTION="EXCEPTION"

def log(*, type: LogLevel, message: any):
    custom_dimensions_extras = None 

    if isinstance(message, str):
        message = {"message": message}
    elif isinstance(message, dict):
        message = {
            k:v for k,v in message.items() if v is not None
        }

        custom_dimensions = message 

        custom_dimensions_extras = {
            "custom_dimensions": custom_dimensions
        }
    
    if type == LogLevel.DEBUG:
        logger.debug(message, extra=custom_dimensions_extras)
    elif type == LogLevel.INFO:
        logger.info(message, extra=custom_dimensions_extras)
    elif type == LogLevel.WARNING:
        logger.warning(message, extra=custom_dimensions_extras)
    elif type == LogLevel.ERROR:
        logger.error(message, extra=custom_dimensions_extras)
    elif type == LogLevel.CRITICAL:
        logger.critical(message, extra=custom_dimensions_extras)
    elif type == LogLevel.EXCEPTION:
        logger.exception(message, extra=custom_dimensions_extras)
