import logging
import logging.config
import sys
from pythonjsonlogger import jsonlogger

from app.core.config import settings


def setup_logging():
    """
    Configure JSON logging for the application.
    Logs include: timestamp, level, logger, message, and any extra fields.
    """
    log_level = getattr(logging, settings.LOG_LEVEL, logging.INFO)
    
    # Create a JSON formatter
    json_formatter = jsonlogger.JsonFormatter(
        fmt='%(timestamp)s %(level)s %(logger)s %(message)s',
        timestamp=True
    )
    
    # Create a stream handler for stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(json_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    
    return root_logger
