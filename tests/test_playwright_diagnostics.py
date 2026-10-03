"""Интеграция pytest-плагинов с подставным браузером и настоящим Allure."""

import json
from pathlib import Path

import pytest


pytest_plugins = ["pytester"]


FAKE_BROWSER = '''
import importlib.abc
from pathlib import Path
from types import SimpleNamespace
import sys
import pytest

class BlockAllure(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"allure", "allure_pytest", "allure_commons"}:
            raise ImportError("Allure отключён для проверки независимости")

if BLOCK_ALLURE:
    sys.meta_path.insert(0, BlockAllure())

pytest_plugins = PLUGINS

def record(event):
    with Path("lifecycle.txt").open("a", encoding="utf-8") as output:
        output.write(event + "\\n")

class Page:
    def is_closed(self):
        return SCENARIO == "closed"

    def screenshot(self, *, path, full_page):
        if SCENARIO == "screenshot_error":
            raise RuntimeError("Ошибка скриншота")
        Path(path).write_bytes(b"screenshot")

class Tracing:
    def start(self, **kwargs):
        pass

    def stop(self, *, path=None):
        record("trace.stop")
        if path is not None:
            Path(path).write_bytes(b"trace")

class Context:
    tracing = Tracing()

    def new_page(self):
        if SCENARIO == "new_page_error":
            raise RuntimeError("Ошибка создания страницы")
        return Page()

    def close(self):
        record("context.close")
        if SCENARIO == "close_error":
            raise RuntimeError("Ошибка закрытия контекста")

class Browser:
    def new_context(self, **kwargs):
        return Context()

    def close(self):
        record("browser.close")

@pytest.fixture
def playwright():
    return SimpleNamespace(chromium=SimpleNamespace(launch=lambda **kwargs: Browser()))

@pytest.fixture
def qa_browser_settings():
    return SimpleNamespace(engine="chromium", headless=True, width=800,
                           height=600, ignore_https_errors=False)

@pytest.fixture
def broken_setup(browser_page):
    raise RuntimeError("Ошибка зависимой фикстуры")
'''


def run_browser_test(pytester, monkeypatch, scenario: str, reporter: str):
    """Запускает отдельный pytest с выбранными расширениями и сценарием."""
    pytest.importorskip("playwright")
    pytest.importorskip("pydantic")
    pytest.importorskip("yaml")
    if reporter != "none":
        pytest.importorskip("allure")
    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).resolve().parents[1]))
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    monkeypatch.setenv("PYTHONIOENCODING", "utf-8")
    plugins = ["qa_core.pytest_plugins.playwright"]
    if reporter == "first":
        plugins.insert(0, "qa_core.pytest_plugins.allure_reporting")
    elif reporter == "last":
        plugins.append("qa_core.pytest_plugins.allure_reporting")
    pytester.makeconftest(
        f"BLOCK_ALLURE = {reporter == 'none'!r}\n"
        f"PLUGINS = {plugins!r}\nSCENARIO = {scenario!r}\n" + FAKE_BROWSER
    )
    fixture = "broken_setup" if scenario == "setup" else "browser_page"
    assertion = "True" if scenario in {"pass", "close_error"} else "False"
    pytester.makepyfile(f"def test_browser({fixture}):\n    assert {assertion}\n")
    arguments = ["-q", "-p", "no:cacheprovider", "--qa-artifacts-dir=diagnostics"]
    if reporter != "none":
        arguments += ["-p", "allure_pytest", "--alluredir=allure-results"]
    return pytester.runpytest_subprocess(*arguments)


@pytest.mark.parametrize("reporter", ["none", "first", "last"])
@pytest.mark.parametrize("scenario", ["pass", "call", "setup"])
def test_diagnostics_with_optional_reporter(pytester, monkeypatch, scenario, reporter):
    """Файлы сохраняются без Allure и прикладываются при любом порядке плагинов."""
    result = run_browser_test(pytester, monkeypatch, scenario, reporter)
    if scenario == "pass":
        result.assert_outcomes(passed=1)
        assert not (pytester.path / "diagnostics").exists()
    else:
        result.assert_outcomes(**{"errors" if scenario == "setup" else "failed": 1})
        assert len(list((pytester.path / "diagnostics").rglob("screenshot.png"))) == 1
        assert len(list((pytester.path / "diagnostics").rglob("playwright-trace.zip"))) == 1
    assert (pytester.path / "lifecycle.txt").read_text().splitlines() == [
        "trace.stop", "context.close", "browser.close"
    ]
    if reporter != "none":
        attachments = []
        for path in (pytester.path / "allure-results").glob("*.json"):
            document = json.loads(path.read_text(encoding="utf-8"))
            for fixture in document.get("afters", []):
                attachments.extend(fixture.get("attachments", []))
        browser_attachments = [
            attachment for attachment in attachments
            if attachment["type"] in {"image/png", "application/zip"}
        ]
        assert len(browser_attachments) == (0 if scenario == "pass" else 2)
        for attachment in browser_attachments:
            path = pytester.path / "allure-results" / attachment["source"]
            expected = b"screenshot" if attachment["type"] == "image/png" else b"trace"
            assert path.read_bytes() == expected


@pytest.mark.parametrize("scenario", ["closed", "screenshot_error"])
def test_trace_survives_unavailable_screenshot(pytester, monkeypatch, scenario):
    """Закрытая страница и ошибка скриншота не мешают сохранению trace."""
    result = run_browser_test(pytester, monkeypatch, scenario, "none")
    result.assert_outcomes(failed=1)
    assert not list((pytester.path / "diagnostics").rglob("screenshot.png"))
    assert len(list((pytester.path / "diagnostics").rglob("playwright-trace.zip"))) == 1
    assert (pytester.path / "lifecycle.txt").read_text().splitlines()[-2:] == [
        "context.close", "browser.close"
    ]


@pytest.mark.parametrize("scenario", ["new_page_error", "close_error"])
def test_browser_closes_on_lifecycle_errors(pytester, monkeypatch, scenario):
    """Браузер закрывается при ошибке создания страницы или закрытия контекста."""
    result = run_browser_test(pytester, monkeypatch, scenario, "none")
    if scenario == "new_page_error":
        result.assert_outcomes(errors=1)
    else:
        result.assert_outcomes(passed=1, errors=1)
    assert (pytester.path / "lifecycle.txt").read_text().splitlines()[-2:] == [
        "context.close", "browser.close"
    ]
