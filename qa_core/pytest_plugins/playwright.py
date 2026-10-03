"""Жизненный цикл Playwright с независимой файловой диагностикой.

Зачем нужен файл:
    Плагин даёт тесту готовую фикстуру ``browser_page``, закрывает
    браузер после теста, а при падении сохраняет скриншот и trace.
    Подключённые отчётчики получают файлы через общий pytest-hook.

Как подключить:
    pytest_plugins = [
        "qa_core.pytest_plugins.playwright",
    ]

Проект может переопределить фикстуру ``qa_browser_settings``, если берёт
настройки не из корневого ``config.yaml``.
"""

from __future__ import annotations

import logging
import pytest
from playwright.sync_api import Page, Playwright

from qa_core.config import BrowserSettings, load_settings
from qa_core.diagnostics import DiagnosticArtifact


pytest_plugins = ["qa_core.pytest_plugins.diagnostics"]
logger = logging.getLogger(__name__)


@pytest.fixture
def qa_browser_settings() -> BrowserSettings:
    """Возвращает настройки Playwright; может быть переопределена проектом."""
    return load_settings().browser


@pytest.fixture
def browser_page(
    playwright: Playwright,
    qa_browser_settings: BrowserSettings,
    request,
    qa_artifact_dir,
) -> Page:
    """Запускает браузер и сохраняет диагностику при падении setup или call."""
    browser_type = getattr(playwright, qa_browser_settings.engine)
    browser = browser_type.launch(headless=qa_browser_settings.headless)
    context = None
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
        try:
            if context is not None:
                context.close()
        finally:
            browser.close()


def _publish_artifact(request, artifact: DiagnosticArtifact) -> None:
    """Сообщает путь в логах и передаёт файл подключённым отчётчикам."""
    logger.info("%s: %s", artifact.name, artifact.path)
    request.config.hook.pytest_qa_attach_artifact(item=request.node, artifact=artifact)
