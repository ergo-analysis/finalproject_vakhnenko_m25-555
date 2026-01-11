import logging
import logging.handlers
from pathlib import Path


def configure_logging():
    """Настройка логирования для всего приложения"""
    
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_format = "%(levelname)s %(asctime)s %(message)s"
    date_format = "%Y-%m-%dT%H:%M:%S"
    
    # логгер приложения
    logger = logging.getLogger("valutatrade")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "actions.log",
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(log_format, datefmt=date_format)
    file_handler.setFormatter(file_formatter)
    
    logger.addHandler(file_handler)
    
    # Логгер для обновления курсов
    rates_logger = logging.getLogger("rates_operations")
    rates_logger.setLevel(logging.INFO)
    rates_logger.handlers.clear()
    
    rates_file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "actions.log",
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    rates_file_handler.setLevel(logging.INFO)
    rates_file_formatter = logging.Formatter(log_format, datefmt=date_format)
    rates_file_handler.setFormatter(rates_file_formatter)
    
    rates_logger.addHandler(rates_file_handler)
    rates_logger.propagate = False
    
    # Логгируем старт приложения
    logger.info("Приложение ValutaTrade Hub запущено")
    
    return logger


def get_logger(name: str = "valutatrade"):
    """Возвращает настроенный логгер"""
    return logging.getLogger(name)