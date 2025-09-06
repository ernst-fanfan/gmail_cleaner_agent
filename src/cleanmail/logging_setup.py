import logging
import sys


def setup_logging(verbosity: int = 0) -> None:
    """Configure structured logging for the application.

    - Sets log level based on verbosity.
    - Configures console handler.
    - Adds timestamps to log records.
    """

    level = logging.INFO
    if verbosity >= 2:
        level = logging.DEBUG
    elif verbosity == 1:
        level = logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

