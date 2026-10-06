"""Жизненный цикл Playwright с независимой файловой диагностикой.

Зачем нужен файл:
    Плагин даёт тесту готовую фикстуру ``browser_page``. Браузер запускается
    один раз на весь запуск, а каждый тест получает свой чистый контекст и
    страницу (cookies и хранилище не переходят между тестами). При падении
    теста скриншот и trace сохраняются в ``test-artifacts/``; если установлен
    allure, они прикладываются и к отчёту. Без allure плагин работает так же.

Как подключить:
    pytest_plugins = [
        "qa_core.pytest_plugins.playwright",
    ]

Чтобы тесты начинались уже после входа в систему, проект переопределяет
фикстуру ``qa_storage_state`` (пример — в examples/test_06_ui_login.py).

Проект может переопределить фикстуру ``qa_browser_settings``, если берёт
настройки не из корневого ``config.py``. Переопределённая фикстура должна
иметь ``scope="session"``, потому что от неё зависит общий браузер.
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Literal

import pytest
from playwright.sync_api import Browser, Page, Playwright
from pydantic import BaseModel, ConfigDict, Field

from qa_core.config import load_section

logger = logging.getLogger(__name__)


class BrowserSettings(BaseModel):
    """Секция ``BROWSER`` файла config.py."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    engine: Literal["chromium", "firefox", "webkit"] = "chromium"
    headless: bool = True
    width: int = Field(default=1920, gt=0)
    height: int = Field(default=1080, gt=0)
    ignore_https_errors: bool = True


def pytest_addoption(parser) -> None:
    parser.getgroup("qa-core").addoption(
        "--qa-artifacts-dir",
        default="test-artifacts",
        help="Куда сохранять скриншоты и trace упавших тестов",
    )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Сохраняет отчёт стадии на тесте как ``report_<стадия>``."""
    del call
    outcome = yield
    setattr(item, f"report_{outcome.get_result().when}", outcome.get_result())


@pytest.fixture
def qa_artifact_dir(request) -> Path:
    """Отдельная папка для файлов одного теста (создаётся только при сбое)."""
    root = Path(request.config.getoption("--qa-artifacts-dir"))
    if not root.is_absolute():
        root = request.config.rootpath / root
    name = re.sub(r"[^\w.-]+", "_", request.node.name)[:80]
    digest = hashlib.sha256(request.node.nodeid.encode("utf-8")).hexdigest()[:12]
    return root / f"{name}-{digest}"


@pytest.fixture(scope="session")
def qa_browser_settings() -> BrowserSettings:
    """Возвращает настройки Playwright; может быть переопределена проектом."""
    return load_section("browser", BrowserSettings)


@pytest.fixture(scope="session")
def qa_browser(
    playwright: Playwright,
    qa_browser_settings: BrowserSettings,
) -> Iterator[Browser]:
    """Запускает браузер один раз на весь запуск и закрывает его в конце."""
    browser_type = getattr(playwright, qa_browser_settings.engine)
    browser = browser_type.launch(headless=qa_browser_settings.headless)
    yield browser
    browser.close()


@pytest.fixture(scope="session")
def qa_storage_state() -> dict | str | None:
    """Состояние браузера (cookies, localStorage) для каждой страницы теста.

    По умолчанию ``None``: страница чистая. Чтобы войти в систему один раз и
    использовать вход во всех тестах, проект переопределяет фикстуру и
    возвращает результат ``context.storage_state()``.
    """
    return None


@pytest.fixture
def browser_page(
    qa_browser: Browser,
    qa_browser_settings: BrowserSettings,
    qa_storage_state: dict | str | None,
    request,
    qa_artifact_dir,
) -> Iterator[Page]:
    """Открывает чистую страницу и сохраняет диагностику при падении."""
    context = qa_browser.new_context(
        storage_state=qa_storage_state,
        viewport={
            "width": qa_browser_settings.width,
            "height": qa_browser_settings.height,
        },
        ignore_https_errors=qa_browser_settings.ignore_https_errors,
    )
    try:
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()

        yield page

        setup_report = getattr(request.node, "report_setup", None)
        call_report = getattr(request.node, "report_call", None)
        test_failed = any(
            report is not None and report.failed
            for report in (setup_report, call_report)
        )

        if test_failed:
            qa_artifact_dir.mkdir(parents=True, exist_ok=True)
            if not page.is_closed():
                screenshot_path = qa_artifact_dir / "screenshot.png"
                try:
                    page.screenshot(path=str(screenshot_path), full_page=True)
                except Exception:
                    logger.exception("Не удалось сохранить скриншот при падении")
                else:
                    _publish(screenshot_path, "Скриншот при падении", "image/png", "png")

            trace_path = qa_artifact_dir / "playwright-trace.zip"
            context.tracing.stop(path=trace_path)
            _publish(trace_path, "Playwright trace", "application/zip", "zip")
        else:
            context.tracing.stop()
    finally:
        context.close()


def _publish(path: Path, name: str, media_type: str, extension: str) -> None:
    """Пишет путь в лог и прикладывает файл к Allure, если он установлен."""
    logger.info("%s: %s", name, path)
    try:
        import allure
    except ImportError:
        return
    allure.attach.file(str(path), name=name, attachment_type=media_type, extension=extension)
