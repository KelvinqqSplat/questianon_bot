import logging, os
from logging.handlers import RotatingFileHandler

def setup_logging(level=logging.INFO):
    os.makedirs("logs", exist_ok=True)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(level)
    # Console
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    root.addHandler(ch)
    # Rotating file
    fh = RotatingFileHandler("logs/app.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    fh.setFormatter(formatter)
    root.addHandler(fh)
