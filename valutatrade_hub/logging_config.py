import logging
import logging.handlers
from pathlib import Path

def configure_logging():
    """Настройка логирования для всего приложения"""
    
    # Создаем директорию где буудт логи
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Формал тога из тз
    log_format = "%(levelname)s %(asctime)s %(message)s"
    date_format = "%Y-%m-%dT%H:%M:%S"
    
    # Создаем логгер приложения
    logger = logging.getLogger("valutatrade")
    logger.setLevel(logging.INFO)
    
    # Удаляем старые обработчики
    logger.handlers.clear()
    
    #обработчик с ротацией
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "actions.log",
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(log_format, datefmt=date_format)
    file_handler.setFormatter(file_formatter)
    
    # тот же обработчик, только другой, без timestamp 
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)
    
    # Добавляем обработчики
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Логгируем старт приложения
    logger.info("Приложение ValutaTrade Hub запущено")
    
    return logger


def get_logger(name: str = "valutatrade"):
    """Возвращает настроенный логгер"""
    return logging.getLogger(name)