#!/usr/bin/env python3
import os
import sys

from dotenv import load_dotenv

load_dotenv() 
#API загрузится из переменной окружения, в коде его нет 
#load_dotenv нужно загрузить перед другими файлами, они на него ссылаются, 
# поэтому тут стоит игнор линтера для импортов

from valutatrade_hub.cli.interface import main # noqa
from valutatrade_hub.logging_config import configure_logging # noqa

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

configure_logging()

if __name__ == "__main__":
    main()