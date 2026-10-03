"""Общий pytest-плагин для диагностических вложений Allure.

Зачем нужен файл:
    Плагин прикладывает накопленные логи упавшего теста и готовые файлы
    диагностических расширений к Allure. При передаче ``--qa-environment``
    также создаёт ``environment.xml`` рядом с результатами Allure.

Как подключить в ``conftest.py`` проекта:
    Сначала установите необязательный набор ``qa-core[allure]``.
    pytest_plugins = ["qa_core.pytest_plugins.allure_reporting"]

Плагин не знает названий проектов, URL или учётных данных. Декораторы и шаги
``allure`` остаются в самих проектных тестах, где формируют бизнес-сценарий.
"""

from pathlib import Path
from xml.etree import ElementTree

import allure
import pytest

from qa_core.diagnostics import DiagnosticArtifact


pytest_plugins = ["qa_core.pytest_plugins.diagnostics"]


def pytest_qa_attach_artifact(item, artifact: DiagnosticArtifact) -> None:
    """Прикладывает готовый файл от любого диагностического расширения."""
    allure.attach.file(
        str(artifact.path),
        name=artifact.name,
        attachment_type=artifact.media_type,
        extension=artifact.extension,
    )


def pytest_addoption(parser) -> None:
    """Добавляет необязательное имя окружения в командную строку pytest."""
    group = parser.getgroup("qa-core")
    group.addoption(
        "--qa-environment",
        action="store",
        default=None,
        help="Имя окружения для environment.xml в Allure-результатах",
    )


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

