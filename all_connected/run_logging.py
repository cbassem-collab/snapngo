import functools
import logging
import sys
import traceback
import warnings
from pathlib import Path
from typing import Optional

_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

# Avoid duplicate handlers if module reloaded
_CONFIGURED = set()


def _safe_filename(name: str) -> str:
    """Turn __name__ or path into a safe log filename."""
    if name == "__main__":
        # When run as script, use script basename
        main = Path(sys.argv[0]).resolve()
        return main.stem + ".log"
    base = name.replace(".", "_")
    for c in '<>:"/\\|?*':
        base = base.replace(c, "_")
    return base + ".log"


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Return a logger that writes only to logs/<name>.log (one file per module).
    """
    name = name or __name__
    logger_name = f"snapngo.{name}"
    logger = logging.getLogger(logger_name)
    if logger_name in _CONFIGURED:
        return logger
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    log_path = _LOG_DIR / _safe_filename(name if name != "__main__" else Path(sys.argv[0]).stem)
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    _CONFIGURED.add(logger_name)
    return logger


def log_step(logger: logging.Logger, message: str, **kwargs):
    """Log a single step with optional key=value context (no secrets)."""
    if kwargs:
        parts = [f"{k}={v!r}" for k, v in kwargs.items()]
        message = f"{message} | " + " ".join(parts)
    logger.info(message)
    # mirroring into combined.log
    # combined.log has all log steps from all modules
    try:
        root = get_root_logger()
        short = logger.name.replace("snapngo.", "", 1) if logger.name.startswith("snapngo.") else logger.name
        root.info(f"{short} | {message}")
    except Exception:
        pass


def log_calls(logger: logging.Logger):
    """Decorator: log function entry (args) and exit (return/exception)."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__name__}"
            try:
                arg_repr = []
                if args:
                    arg_repr.append(f"args_len={len(args)}")
                if kwargs:
                    arg_repr.append(f"kwargs={list(kwargs.keys())}")
                logger.debug(f"ENTER {func_name} " + " ".join(arg_repr))
            except Exception:
                logger.debug(f"ENTER {func_name}")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"EXIT {func_name} ok")
                return result
            except Exception as e:
                logger.exception(f"EXIT {func_name} error: {e}")
                raise

        return wrapper

    return decorator


# Root snapngo logger also writes a combined log for cross-file timeline
def get_root_logger():
    """Single combined log file for all modules (optional)."""
    logger = logging.getLogger("snapngo")
    if getattr(get_root_logger, "_done", False):
        return logger
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    combined = _LOG_DIR / "combined.log"
    fh = logging.FileHandler(combined, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    logger.addHandler(fh)
    get_root_logger._done = True
    return logger


def setup_error_logging():
    """
    Capture warnings and uncaught exceptions to logs/errors.log.
    Call once at app startup (bot.py, connections.py).
    """
    if getattr(setup_error_logging, "_done", False):
        return
    setup_error_logging._done = True

    errors_path = _LOG_DIR / "errors.log"
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Log Python warnings (FutureWarning, DeprecationWarning, etc.) to errors.log
    warnings_logger = logging.getLogger("py.warnings")
    fh_warn = logging.FileHandler(errors_path, encoding="utf-8")
    fh_warn.setLevel(logging.WARNING)
    fh_warn.setFormatter(fmt)
    warnings_logger.addHandler(fh_warn)
    logging.captureWarnings(True)

    # Log WARNING+ from root (third-party libs) to errors.log
    root = logging.getLogger()
    fh_root = logging.FileHandler(errors_path, encoding="utf-8")
    fh_root.setLevel(logging.WARNING)
    fh_root.setFormatter(fmt)
    root.addHandler(fh_root)

    # Log uncaught exceptions
    _orig_excepthook = sys.excepthook

    def _excepthook(exc_type, exc_value, exc_tb):
        err_logger = logging.getLogger("snapngo.errors")
        if not err_logger.handlers:
            fh = logging.FileHandler(errors_path, encoding="utf-8")
            fh.setFormatter(fmt)
            err_logger.addHandler(fh)
        err_logger.critical(
            "Uncaught exception:\n%s",
            "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
        )
        _orig_excepthook(exc_type, exc_value, exc_tb)

    sys.excepthook = _excepthook
