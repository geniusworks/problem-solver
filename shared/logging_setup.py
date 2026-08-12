"""Application logging configuration.

A one-function module, pulled out of the old shared/utils.py grab-bag so
callers that only want logging don't drag in the AoC HTTP/caching stack.
"""

import logging
import os
from typing import Optional


def setup_logging(year: Optional[int] = None, day: Optional[int] = None) -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )

    # Quieten noisy third-party loggers.
    logging.getLogger("blib2to3").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.INFO)
    logging.getLogger("asyncio").setLevel(logging.INFO)
