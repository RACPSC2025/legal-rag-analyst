import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Configuración básica
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d) — %(message)s"
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

def get_logger(name: str, level=logging.INFO):
    """Retorna un logger configurado con consola y archivo rotativo."""
    logger = logging.getLogger(name)
    
    if logger.hasHandlers():
        return logger
        
    logger.setLevel(level)
    
    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(console_handler)
    
    # Handler para archivo
    file_handler = RotatingFileHandler(
        LOG_DIR / "app.log",
        maxBytes=5*1024*1024, # 5MB
        backupCount=2,
        encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(file_handler)
    
    return logger
