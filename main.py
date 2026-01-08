#!/usr/bin/env python3
import sys
import os
from valutatrade_hub.cli.interface import main
from valutatrade_hub.logging_config import configure_logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

configure_logging()

if __name__ == "__main__":
    # Инициализируем логирование
    configure_logging()
    main()