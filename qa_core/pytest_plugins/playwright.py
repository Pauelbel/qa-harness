"""Playwright lifecycle с диагностикой Allure.

Зачем нужен файл:
    Плагин даёт тесту готовую фикстуру ``browser_page``, закрывает
    браузер после теста, а при падении прикладывает скриншот и trace.

Как подключить:
    pytest_plugins = [
        "qa_core.pytest_plugins.allure_reporting",
        "qa_core.pytest_plugins.playwright",
    ]

Проект может переопределить фикстуру ``qa_browser_settings``, если берёт
настройки не из корневого ``config.yaml``.
"""

from __future__ import annotations

from typing import Literal

import allure
import pytest
from playwright.sync_api import Page, Playwright
from pydantic import BaseModel, ConfigDict, Field

from qa_core.config import load_section


class BrowserSettings(BaseModel):
    """Секция ``browser`` файла config.yaml."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    engine: Literal["chromium", "firefox", "webkit"] = "chromium"
    headless: bool = True
    width: int = Field(default=1920, gt=0)
    height: int = Field(default=1080, gt=0)
    ignore_https_errors: bool = True


@pytest.fixture
def qa_browser_settings() -> BrowserSettings:
    """Возвращает настройки Playwright; может быть переопределена проектом."""
    return load_section("browser", BrowserSettings)


@pytest.fixture
def browser_page(
    playwright: Playwright,
    qa_browser_settings: BrowserSettings,
    request,
    tmp_path,
) -> Page:
    """Запускает браузер и прикладывает диагностику при падении."""
    browser_type = getattr(playwright, qa_browser_settings.engine)
    browser = browser_type.launch(headless=qa_browser_settings.headless)
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
        browser.close()
