#!/usr/bin/env python3
from valutatrade_hub.cli.interface import main
from valutatrade_hub.logging_config import configure_logging

if __name__ == "__main__":
    # Инициализируем логирование
    configure_logging()
    main()