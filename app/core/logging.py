import logging
import json
import sys
import uuid
from datetime import datetime
from typing import Dict, Any, Optional


# Custom JSON formatter for structured logging
class JSONFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings after parsing the log record.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        log_record = self._format_record(record)
        return json.dumps(log_record)

    def _format_record(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Create a dictionary from a log record."""
        # Start with basic record attributes
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add any custom attributes
        for key, value in record.__dict__.items():
            if key not in log_record and not key.startswith('_') and isinstance(value,
                                                                                (str, int, float, bool, type(None))):
                log_record[key] = value

        # Add traceback for exceptions
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return log_record


class RequestIDFilter(logging.Filter):
    """
    Filter that adds a request_id to the log record if not present.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, 'request_id'):
            record.request_id = str(uuid.uuid4())
        return True


def setup_logging(logger_name: str = "app", log_level: str = "INFO") -> logging.Logger:
    """
    Set up structured logging with JSON formatting.

    Args:
        logger_name: Name for the logger
        log_level: Logging level to use

    Returns:
        Logger instance
    """
    # Create logger
    logger = logging.getLogger(logger_name)

    # Set log level
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)

    # Clear any existing handlers
    logger.handlers = []

    # Create console handler that outputs to stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    # Add request ID filter
    handler.addFilter(RequestIDFilter())

    # Add handler to logger
    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


# Get a new logger with request context
def get_logger(
        module_name: str,
        request_id: Optional[str] = None,
        user_id: Optional[int] = None
) -> logging.Logger:
    """
    Get a logger for a specific module with request context.

    Args:
        module_name: Name of the module (usually __name__)
        request_id: Current request ID
        user_id: ID of the authenticated user

    Returns:
        Logger with context
    """
    logger = logging.getLogger(f"app.{module_name}")

    # Create a new logger with request context
    extra = {}

    if request_id:
        extra['request_id'] = request_id

    if user_id:
        extra['user_id'] = user_id

    if extra:
        return logging.LoggerAdapter(logger, extra)

    return logger