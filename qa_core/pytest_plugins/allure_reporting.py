"""Общий pytest-плагин для диагностических вложений Allure.

Зачем нужен файл:
    Плагин запоминает результат каждой стадии pytest и, если тест упал,
    прикладывает накопленные логи к Allure. При передаче ``--qa-environment``
    также создаёт ``environment.xml`` рядом с результатами Allure.

Как подключить в ``conftest.py`` проекта:
    pytest_plugins = ["qa_core.pytest_plugins.allure_reporting"]

Плагин не знает названий проектов, URL или учётных данных. Декораторы и шаги
``allure`` остаются в самих проектных тестах, где формируют бизнес-сценарий.
"""

from pathlib import Path
from xml.etree import ElementTree

import allure
import pytest

from qa_core.pytest_plugins._shared import (
    add_environment_option,
    pytest_runtest_makereport,  # noqa: F401 — хук регистрируется как часть плагина
)


def pytest_addoption(parser) -> None:
    """Добавляет необязательное имя окружения в командную строку pytest."""
    add_environment_option(parser)


def pytest_sessionfinish(session, exitstatus) -> None:
    """Записывает окружение запуска, если настроены Allure и имя окружения."""
    del exitstatus
    allure_dir = session.config.getoption("--alluredir", default=None)
    environment = session.config.getoption("--qa-environment", default=None)
    if not allure_dir or not environment:
        return

    output_dir = Path(allure_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    root = ElementTree.Element("environment")
    parameter = ElementTree.SubElement(root, "parameter")
    ElementTree.SubElement(parameter, "key").text = "Окружение запуска тестов"
    ElementTree.SubElement(parameter, "value").text = environment
    ElementTree.ElementTree(root).write(
        output_dir / "environment.xml",
        encoding="utf-8",
        xml_declaration=True,
    )


@pytest.fixture(autouse=True)
def attach_logs_on_failure(request, caplog):
    """Прикладывает к Allure логи setup и call только при падении теста."""
    yield

    report = getattr(request.node, "report_call", None)
    if report is None or not report.failed:
        return

    records = caplog.get_records("setup") + caplog.get_records("call")
    if not records:
        return

    log_text = "\n".join(caplog.handler.format(record) for record in records)
    allure.attach(
        log_text,
        name="Контекст ошибки: логи теста",
        attachment_type=allure.attachment_type.TEXT,
    )

