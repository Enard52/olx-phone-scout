import logging

from loguru import logger

from src.core import config
from src.infrastructure import logging as logging_cfg


def test_display_path_is_relative_to_repo():
    assert str(config.display_path(config.DATA_DIR / "sessions" / "x")) == "data/sessions/x"


def test_display_path_keeps_paths_outside_repo():
    assert str(config.display_path("/elsewhere/file.json")) == "/elsewhere/file.json"


def test_console_hides_library_info_but_keeps_app_messages(capsys):
    logging_cfg.configure_logging(app_name="test", enqueue=False)

    logging.getLogger("httpx").info('HTTP Request: GET https://www.olx.kz "HTTP/1.1 200 OK"')
    logging.getLogger("httpx").warning("library warning")
    logger.info("app message")

    err = capsys.readouterr().err
    assert "HTTP Request" not in err
    assert "library warning" in err
    assert "app message" in err
    assert "| INFO" not in err  # no timestamp/level prefix on plain INFO lines
