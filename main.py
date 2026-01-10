#!/usr/bin/env python3
import sys
import os
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from valutatrade_hub.logging_config import configure_logging
configure_logging()

from valutatrade_hub.cli.interface import main

if __name__ == "__main__":
    main()