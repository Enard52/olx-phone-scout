#!/usr/bin/env python3
"""
Async-safe Loguru configuration for olx analyzer.

- Call configure_logging(...) once at startup (before other modules log).
- Then use `from src.infrastructure.logging import logger` and call logger.info(...).
- Optionally keep `from src.infrastructure.logging import get_logger` for compatibility.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger
from tqdm import tqdm

from src.core import config

if TYPE_CHECKING:
    from loguru import Record

# Default rotation/retention values (adjust to taste)
DEFAULT_ROTATION = "10 MB"  # or "00:00" for daily
DEFAULT_RETENTION = "14 days"
DEFAULT_COMPRESSION = "zip"


def get_log_dir() -> Path:
    """
    Resolve logs directory. Tries project config.get_logs_dir, falls back to repo path.
    """
    try:
        # Lazy import to avoid circular imports

        p = Path(config.get_logs_dir())
        p.mkdir(parents=True, exist_ok=True)
        return p
    except Exception:
        # Fallback: emulate your earlier structure under data/sessions/.../logs
        p = Path(__file__).resolve().parent.parent.parent / "data" / "sessions" / "logs"
        p.mkdir(parents=True, exist_ok=True)
        return p


# --- filters to route records to specific sinks based on module/name ---
def module_is_one_of(*module_names: str) -> Callable[[dict], bool]:
    names = set(module_names)
    return lambda record: (record.get("module") or "") in names


def module_startswith(prefix: str) -> Callable[[dict], bool]:
    return lambda record: (record.get("module") or "").startswith(prefix)


def module_matches_any(prefixes: Iterable[str]) -> Callable[[dict], bool]:
    prefixes = tuple(prefixes)
    return lambda record: any((record.get("module") or "").startswith(p) for p in prefixes)


def _tqdm_safe_write(message: str) -> None:
    # tqdm.write prints above active progress bars instead of breaking them
    tqdm.write(message, end="", file=sys.stderr)


def _console_filter(record: Record) -> bool:
    return record["level"].no >= logging.WARNING or not record["extra"].get("stdlib")


def _console_format(record: Record) -> str:
    if record["level"].no >= logging.WARNING:
        return "<level>{level}</level>: {message}\n{exception}"
    return "{message}\n{exception}"


# --- public API: configure_logging, get_logger, logger (loguru) ---
def configure_logging(  # noqa: PLR0913
    *,
    app_name: str = "app",
    level: str = "INFO",
    console_level: str | None = None,
    rotation: str | int = DEFAULT_ROTATION,
    retention: str | int | None = DEFAULT_RETENTION,
    compression: str | None = DEFAULT_COMPRESSION,
    enqueue: bool = True,
) -> None:
    """
    Configure loguru with an async-safe console + multiple file sinks and stdlib interception.

    Call once very early, e.g.:
        from src.infrastructure import logging as logging_cfg
        logging_cfg.configure_logging(app_name="olx_analyzer", level="INFO")
    """
    console_level = console_level or level

    # Remove previous sinks to avoid duplicates (safe to call multiple times during tests)
    logger.remove()

    # Console sink: plain messages from the app; library INFO/DEBUG (httpx requests) goes to files only
    logger.add(
        _tqdm_safe_write,
        level=console_level,
        format=_console_format,
        filter=_console_filter,
        colorize=True,
        backtrace=True,
        diagnose=False,
        enqueue=enqueue,
        catch=True,
    )

    # Log directory
    log_dir = get_log_dir()

    # Module -> filename routing. Tune these entries to match your repo module names.
    # Each tuple is (filter_callable, filename)
    routing: Sequence[tuple[Callable[[dict], bool], str]] = [
        # async-prefixed modules (adjust prefixes to match your module `__name__`)
        (module_matches_any(("async_scraper", "async_")), "async_scraper.log"),
        (module_matches_any(("scraper", "scrapers")), "scraper.log"),
        (module_is_one_of("analyzer"), "analyzer.log"),
        (module_matches_any(("free_cloud_llm", "gemini_api", "ollama_api")), "free_cloud_llm.log"),
        # add more as needed
    ]

    # Add file sinks for each mapping (async-safe via enqueue=True)
    for filt, fname in routing:
        logger.add(
            str(log_dir / fname),
            level=level,
            rotation=rotation,
            retention=retention,
            compression=compression,
            enqueue=enqueue,
            serialize=False,
            filter=filt,  # type: ignore[arg-type]
            catch=True,
        )

    # General fallback log for everything else
    logger.add(
        str(log_dir / f"{app_name}.log"),
        level=level,
        rotation=rotation,
        retention=retention,
        compression=compression,
        enqueue=enqueue,
        serialize=False,
        catch=True,
    )

    # Separate errors file for quick monitoring/alerts
    logger.add(
        str(log_dir / f"{app_name}_errors.log"),
        level="ERROR",
        rotation=rotation,
        retention=retention,
        compression=compression,
        enqueue=enqueue,
        serialize=False,
        catch=True,
    )

    # Intercept standard library logging and forward to Loguru
    class InterceptHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            # Map stdlib level to Loguru
            try:
                level_name = logger.level(record.levelname).name
            except Exception:
                level_name = str(record.levelno)

            # Depth: pick a conservative depth so the real caller is shown.
            # If depth is off, increase/decrease; this is fine for async apps.
            logger.bind(stdlib=True).opt(depth=6, exception=record.exc_info).log(
                level_name, record.getMessage()
            )

    root = logging.getLogger()
    root.handlers[:] = [InterceptHandler()]
    root.setLevel(0)

    # Safe startup info via logger (goes to console + fallback file)
    logger.debug("Logging initialized; logs directory: {}", str(log_dir))


def get_logger(name: str):
    """
    Backwards-compatible helper (optional). Returns a bound logger with module extra.
    You can keep using `get_logger(__name__)` if you have existing code that imports it.
    """
    return logger.bind(module=name)


# Export the Loguru logger object for direct usage
# Usage in modules:
#   from src.infrastructure.logging import logger
#   logger.info("hello")
#
# Or keep using your older pattern:
#   from src.infrastructure.logging import get_logger
#   logger = get_logger(__name__)
#   logger.info(...)
#
# Both will work; internal sinks route by the record['module'] value.
