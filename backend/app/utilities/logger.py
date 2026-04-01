"""
Logging configuration
"""
import logging
import os
import sys

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


class CompactConsoleFilter(logging.Filter):
    """Reduce console noise while preserving high-value progress and failures."""

    KEEP_INFO_PREFIXES = ("[PROGRESS]", "[RESULT]")

    def __init__(self, mode: str):
        super().__init__()
        self.mode = (mode or "compact").strip().lower()

    def filter(self, record: logging.LogRecord) -> bool:
        if self.mode == "verbose":
            return True

        # Always show warnings/errors in any non-verbose mode.
        if record.levelno >= logging.WARNING:
            return True

        if self.mode == "quiet":
            return False

        # compact mode: keep only explicit progress/result info lines.
        message = record.getMessage()
        return any(message.startswith(prefix) for prefix in self.KEEP_INFO_PREFIXES)


def _build_console_handler() -> logging.Handler:
    mode = os.getenv("CONSOLE_LOG_MODE", "compact")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler.setLevel(logging.INFO)
    handler.addFilter(CompactConsoleFilter(mode=mode))
    return handler


logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[_build_console_handler()],
)

logger = logging.getLogger("aura")

def setup_logging():
    """Configure application logging"""
    pass
