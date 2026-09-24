"""Общая настройка логирования для pytest-проектов.

Плагин включает вывод логов в консоль и сохраняет подробный файл запуска в
папке ``logs`` текущего проекта. Имя окружения берётся из параметра
``--qa-environment`` или переменной ``TEST_ENV``. При сборе тестов без запуска
файл лога не создаётся.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path


def pytest_configure(config) -> None:
    """Настраивает единый формат логов для подключившего Core проекта."""
    environment = (
        config.getoption("--qa-environment", default=None)
        or os.getenv("TEST_ENV")
        or "local"
    )
    environment_tag = f"[{environment.upper()}]".replace("%", "%%")
    console_format = f"[%(levelname)s] {environment_tag} → %(message)s"
    file_format = (
        f"%(asctime)s [%(levelname)s] {environment_tag} "
        "[%(name)s] → %(message)s"
    )

    config.option.log_cli = True
    config.option.log_cli_level = "INFO"
    config.option.log_cli_format = console_format
    config.option.log_format = console_format

    if config.option.collectonly:
        return

    log_directory = Path.cwd() / "logs"
    log_directory.mkdir(exist_ok=True)
    config.option.log_file = str(log_directory / f"pytest_{environment}.log")
    config.option.log_file_level = "DEBUG"
    config.option.log_file_format = file_format
    config.option.log_file_date_format = "%Y-%m-%d %H:%M:%S"

    for logger_name in ("urllib3", "selenium", "httpx", "PIL"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)
