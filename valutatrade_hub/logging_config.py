import logging
import logging.handlers
from pathlib import Path


def configure_logging():
    
    log_directory = Path("logs")
    log_directory.mkdir(exist_ok=True)
    
    log_formatter = logging.Formatter(
        fmt='%(levelname)s %(asctime)s %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S'
    )
    
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_directory / "actions.log",
        maxBytes=5*1024*1024,  # это 5 МБ
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setFormatter(log_formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    
    actions_logger = logging.getLogger('actions')
    actions_logger.setLevel(logging.INFO)
    actions_logger.addHandler(file_handler)
    actions_logger.addHandler(console_handler)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    return actions_logger