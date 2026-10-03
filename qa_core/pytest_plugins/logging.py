"""Общая настройка логирования для pytest-проектов.

Плагин включает вывод логов в консоль и сохраняет подробный файл запуска в
папке ``logs`` текущего проекта. Имя окружения берётся из параметра
``--qa-environment`` или переменной ``TEST_ENV``. При сборе тестов без запуска
файл лога не создаётся.

Плагин задаёт только значения по умолчанию. Всё, что пользователь указал сам,
остаётся в силе: параметры командной строки (``--log-cli-level=DEBUG``,
``--log-file=...``) и значения из ``pytest.ini``. Консольные логи отключаются
параметром ``-o log_cli=false``. Запись ``log_cli = false`` в самом ``pytest.ini``
плагин не отличает от «не задано» и консольные логи включит.
Для отладки достаточно запустить, например:

    python -m pytest --log-cli-level=DEBUG
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from _pytest.logging import DEFAULT_LOG_FORMAT



def add_environment_option(parser) -> None:
    """Добавляет ``--qa-environment``; повторная регистрация другим плагином безопасна."""
    try:
        parser.getgroup("qa-core").addoption(
            "--qa-environment",
            action="store",
            default=None,
            help="Имя окружения для логов и environment.xml в Allure-результатах",
        )
    except ValueError:
        pass


def pytest_addoption(parser) -> None:
    """Добавляет необязательное имя окружения в командную строку pytest."""
    add_environment_option(parser)


def _is_user_set(config, name: str) -> bool:
    """Проверяет, задал ли пользователь настройку логов сам, а не плагин."""
    if config.getoption(name, default=None) is not None:
        return True
    value = config.getini(name)
    if name == "log_format":
        # У этой настройки в pytest есть своё значение по умолчанию, поэтому
        # пользовательским считается только отличающееся от него.
        return value != DEFAULT_LOG_FORMAT
    if value:
        return True
    return _is_overridden(config, name)


def _is_overridden(config, name: str) -> bool:
    """Проверяет, передана ли настройка через ``-o имя=значение``."""
    overrides = config.getoption("override_ini", default=None) or []
    return any(item.split("=", 1)[0].strip() == name for item in overrides)


def _set_default(config, name: str, value) -> None:
    """Применяет значение по умолчанию, не перебивая настройки пользователя."""
    if not _is_user_set(config, name):
        setattr(config.option, name, value)


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

    # Проверка до установки значений по умолчанию, иначе они сойдут за выбор пользователя.
    user_chose_level = any(
        _is_user_set(config, name)
        for name in ("log_level", "log_cli_level", "log_file_level")
    )

    # Pytest включает консольные логи, когда задан уровень ``log_cli_level`` (в
    # командной строке) или ``log_cli = true``, поэтому уровень выставляется всегда,
    # кроме явного ``-o log_cli=false``.
    if not (_is_overridden(config, "log_cli") and not config.getini("log_cli")):
        config.option.log_cli_level = (
            config.getoption("log_cli_level", default=None)
            or config.getini("log_cli_level")
            or "INFO"
        )
    _set_default(config, "log_cli_format", console_format)
    _set_default(config, "log_format", console_format)

    if config.option.collectonly:
        return

    if not _is_user_set(config, "log_file"):
        log_directory = Path.cwd() / "logs"
        log_directory.mkdir(exist_ok=True)
        config.option.log_file = str(log_directory / f"pytest_{environment}.log")
    _set_default(config, "log_file_level", "DEBUG")
    _set_default(config, "log_file_format", file_format)
    _set_default(config, "log_file_date_format", "%Y-%m-%d %H:%M:%S")

    # Шумные библиотеки приглушаются, пока пользователь сам не запросил уровень:
    # при отладке (--log-cli-level=DEBUG) их сообщения нужны.
    if not user_chose_level:
        for logger_name in ("urllib3", "selenium", "httpx", "PIL"):
            logging.getLogger(logger_name).setLevel(logging.WARNING)
