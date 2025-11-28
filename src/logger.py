import logging
import sys
from logging.handlers import RotatingFileHandler
import os
from collections import deque

# Global log buffer
log_buffer = deque(maxlen=50)

class ListHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            log_buffer.append(msg)
        except Exception:
            self.handleError(record)

def setup_logger(name="coffin299", log_level="INFO"):
    """
    Sets up a logger with console and file handlers.
    """
    logger = logging.getLogger(name)
    
    # Convert string level to logging constant
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File Handler
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    # Use standard FileHandler instead of RotatingFileHandler to avoid Windows permission errors
    # during rotation while the file is open.
    file_handler = logging.FileHandler(
        os.path.join(log_dir, "bot.log"),
        encoding='utf-8',
        mode='a'
    )
    file_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # List Handler (for WebUI)
    list_handler = ListHandler()
    list_handler.setFormatter(formatter)
    logger.addHandler(list_handler)
    
    return logger
