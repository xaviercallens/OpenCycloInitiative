"""
OpenCyclo OS — Structured Logger
================================

JSON-lines structured logging with rotating file handler.
All sensor readings and state transitions are logged here for
post-run analysis and growth curve reconstruction.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler


class JSONFormatter(logging.Formatter):
    """Format log records as single-line JSON for easy parsing."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "func": record.funcName,
            "msg": record.getMessage(),
        }
        # Attach extra structured data if present
        if hasattr(record, "data"):
            log_entry["data"] = record.data
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, default=str)


def setup_logger(
    name: str = "opencyclo",
    log_dir: str = "logs",
    log_level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
) -> logging.Logger:
    """
    Create and configure the application logger.

    Args:
        name: Logger name.
        log_dir: Directory for log files.
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR).
        max_bytes: Max size per log file before rotation.
        backup_count: Number of rotated log files to keep.

    Returns:
        Configured logging.Logger instance.
    """
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Prevent duplicate handlers on re-init
    if logger.handlers:
        return logger

    # ── File handler (JSON lines) ────────────
    file_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "opencyclo.jsonl"),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)

    # ── Console handler (human-readable) ─────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s │ %(levelname)-7s │ %(module)s │ %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    logger.addHandler(console_handler)

    return logger


def log_sensor_data(
    logger: logging.Logger,
    sensor: str,
    value: float,
    unit: str,
    **extra,
) -> None:
    """
    Log a sensor reading with structured data.

    Args:
        logger: The application logger.
        sensor: Sensor name (e.g., "ph", "biomass_density", "led_pwm").
        value: Numeric reading.
        unit: Unit string (e.g., "pH", "g/L", "Hz").
        **extra: Additional key-value pairs to attach.
    """
    record = logger.makeRecord(
        name=logger.name,
        level=logging.INFO,
        fn="",
        lno=0,
        msg=f"{sensor}: {value:.4f} {unit}",
        args=(),
        exc_info=None,
    )
    record.data = {"sensor": sensor, "value": value, "unit": unit, **extra}
    logger.handle(record)
