"""Жизненный цикл Playwright с независимой файловой диагностикой.

Зачем нужен файл:
<<<<<<< HEAD
    Плагин даёт тесту готовую фикстуру ``browser_page``, закрывает
    браузер после теста, а при падении сохраняет скриншот и trace.
    Подключённые отчётчики получают файлы через общий pytest-hook.
=======
    Плагин даёт тесту готовую фикстуру ``browser_page``. Браузер запускается
    один раз на весь запуск, а каждый тест получает свой чистый контекст и
    страницу (cookies и хранилище не переходят между тестами). При падении
    теста прикладываются скриншот и trace.
>>>>>>> 4bb577fd1ea6e130ec43756d6213dcc872789e4f

Как подключить:
    pytest_plugins = [
        "qa_core.pytest_plugins.playwright",
    ]

Чтобы тесты начинались уже после входа в систему, проект переопределяет
фикстуру ``qa_storage_state`` (пример — в examples/test_06_ui_login.py).

Проект может переопределить фикстуру ``qa_browser_settings``, если берёт
настройки не из корневого ``config.yaml``. Переопределённая фикстура должна
иметь ``scope="session"``, потому что от неё зависит общий браузер.
"""

from __future__ import annotations

<<<<<<< HEAD
import logging
=======
from collections.abc import Iterator
from typing import Literal

import allure
>>>>>>> 4bb577fd1ea6e130ec43756d6213dcc872789e4f
import pytest
from playwright.sync_api import Browser, Page, Playwright
from pydantic import BaseModel, ConfigDict, Field

<<<<<<< HEAD
from qa_core.config import BrowserSettings, load_settings
from qa_core.diagnostics import DiagnosticArtifact


pytest_plugins = ["qa_core.pytest_plugins.diagnostics"]
logger = logging.getLogger(__name__)
=======
from qa_core.config import load_section
from qa_core.pytest_plugins._shared import (
    pytest_runtest_makereport,  # noqa: F401 — хук регистрируется как часть плагина
)
>>>>>>> 4bb577fd1ea6e130ec43756d6213dcc872789e4f


class BrowserSettings(BaseModel):
    """Секция ``browser`` файла config.yaml."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    engine: Literal["chromium", "firefox", "webkit"] = "chromium"
    headless: bool = True
    width: int = Field(default=1920, gt=0)
    height: int = Field(default=1080, gt=0)
    ignore_https_errors: bool = True


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
<<<<<<< HEAD
    qa_artifact_dir,
) -> Page:
    """Запускает браузер и сохраняет диагностику при падении setup или call."""
    browser_type = getattr(playwright, qa_browser_settings.engine)
    browser = browser_type.launch(headless=qa_browser_settings.headless)
    context = None
=======
    tmp_path,
) -> Iterator[Page]:
    """Открывает чистую страницу и прикладывает диагностику при падении."""
    context = qa_browser.new_context(
        storage_state=qa_storage_state,
        viewport={
            "width": qa_browser_settings.width,
            "height": qa_browser_settings.height,
        },
        ignore_https_errors=qa_browser_settings.ignore_https_errors,
    )
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    page = context.new_page()

    yield page

    setup_report = getattr(request.node, "report_setup", None)
    call_report = getattr(request.node, "report_call", None)
    test_failed = any(
        report is not None and report.failed
        for report in (setup_report, call_report)
    )

>>>>>>> 4bb577fd1ea6e130ec43756d6213dcc872789e4f
    try:
        context = browser.new_context(
            viewport={
                "width": qa_browser_settings.width,
                "height": qa_browser_settings.height,
            },
            ignore_https_errors=qa_browser_settings.ignore_https_errors,
        )
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
                    _publish_artifact(
                        request,
                        DiagnosticArtifact(
                            screenshot_path, "Скриншот при падении", "image/png", "png"
                        ),
                    )

            trace_path = qa_artifact_dir / "playwright-trace.zip"
            context.tracing.stop(path=trace_path)
            _publish_artifact(
                request,
                DiagnosticArtifact(
                    trace_path, "Playwright trace", "application/zip", "zip"
                ),
            )
        else:
            context.tracing.stop()
    finally:
<<<<<<< HEAD
        try:
            if context is not None:
                context.close()
        finally:
            browser.close()


def _publish_artifact(request, artifact: DiagnosticArtifact) -> None:
    """Сообщает путь в логах и передаёт файл подключённым отчётчикам."""
    logger.info("%s: %s", artifact.name, artifact.path)
    request.config.hook.pytest_qa_attach_artifact(item=request.node, artifact=artifact)
=======
        context.close()
>>>>>>> 4bb577fd1ea6e130ec43756d6213dcc872789e4f
