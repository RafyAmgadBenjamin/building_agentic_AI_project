import logging
import sys


class LoggerConfiguration(logging.Formatter):
    COLORS = {
        logging.INFO: "\033[92m",      # Green
        logging.ERROR: "\033[91m",     # Red
        logging.CRITICAL: "\033[91m",  # Red
        logging.WARNING: "\033[93m",   # Yellow
        logging.DEBUG: "\033[94m",     # Blue
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        message = super().format(record)
        return f"{color}{message}{self.RESET}"


def get_logger(name: str = "IacAgentChat", level: int = logging.DEBUG) -> logging.Logger:
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.hasHandlers():
        logger.setLevel(level)
        handler = logging.StreamHandler(sys.stdout)  # Explicitly use stdout
        handler.setFormatter(LoggerConfiguration("%(levelname)s: %(message)s"))
        logger.addHandler(handler)
        logger.propagate = False  # Prevent propagation to root logger
    
    return logger