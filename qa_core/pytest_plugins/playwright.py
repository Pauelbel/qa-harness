"""Playwright lifecycle с диагностикой Allure.

Зачем нужен файл:
    Плагин даёт тесту готовую фикстуру ``browser_page``. Браузер запускается
    один раз на весь запуск, а каждый тест получает свой чистый контекст и
    страницу (cookies и хранилище не переходят между тестами). При падении
    теста прикладываются скриншот и trace.

Как подключить:
    pytest_plugins = [
        "qa_core.pytest_plugins.allure_reporting",
        "qa_core.pytest_plugins.playwright",
    ]

Чтобы тесты начинались уже после входа в систему, проект переопределяет
фикстуру ``qa_storage_state`` (пример — в examples/test_06_ui_login.py).

Проект может переопределить фикстуру ``qa_browser_settings``, если берёт
настройки не из корневого ``config.yaml``. Переопределённая фикстура должна
иметь ``scope="session"``, потому что от неё зависит общий браузер.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Literal

import allure
import pytest
from playwright.sync_api import Browser, Page, Playwright
from pydantic import BaseModel, ConfigDict, Field

from qa_core.config import load_section
from qa_core.pytest_plugins._shared import (
    pytest_runtest_makereport,  # noqa: F401 — хук регистрируется как часть плагина
)


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

    try:
        if test_failed:
            if not page.is_closed():
                allure.attach(
                    page.screenshot(full_page=True),
                    name="Скриншот при падении",
                    attachment_type=allure.attachment_type.PNG,
                )

            trace_path = tmp_path / "playwright-trace.zip"
            context.tracing.stop(path=trace_path)
            allure.attach.file(
                trace_path,
                name="Playwright trace",
                attachment_type="application/zip",
                extension="zip",
            )
        else:
            context.tracing.stop()
    finally:
        context.close()
