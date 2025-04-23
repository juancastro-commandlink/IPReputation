import logging
import sys

class FlushStreamHandler(logging.StreamHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()

# Create a shared logger
logger = logging.getLogger("ipintel")
logger.setLevel(logging.DEBUG)

# Console handler with formatting
console_handler = FlushStreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
console_handler.setFormatter(formatter)

# File handler for subprocess-safe logging
file_handler = logging.FileHandler("api.log", mode="a")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Avoid adding multiple handlers in multiprocessing
if not logger.hasHandlers():
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

# Utility to expose logger for imports
get_logger = lambda: logger