"""Общие pytest-события и каталог файлов для диагностических расширений.

Плагин подключается источниками и отчётчиками автоматически. Он сохраняет
результаты стадий теста и объявляет событие передачи готового файла.
"""

import hashlib
import re
from pathlib import Path

import pytest

from qa_core.diagnostics import DiagnosticArtifact


class DiagnosticHooks:
    """События, которые могут обрабатывать несколько отчётчиков."""

    @pytest.hookspec
    def pytest_qa_attach_artifact(self, item, artifact: DiagnosticArtifact) -> None:
        """Передаёт отчётчикам файл; источник сохраняет его и без обработчиков."""


def pytest_addhooks(pluginmanager) -> None:
    pluginmanager.add_hookspecs(DiagnosticHooks)


def pytest_addoption(parser) -> None:
    group = parser.getgroup("qa-core")
    group.addoption(
        "--qa-artifacts-dir",
        default="test-artifacts",
        help="Каталог диагностических файлов относительно корня проекта",
    )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Сохраняет результаты стадий независимо от подключённых отчётчиков."""
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"report_{report.when}", report)


@pytest.fixture
def qa_artifact_dir(request) -> Path:
    """Возвращает отдельный путь для теста; источник создаёт каталог при сбое."""
    root = Path(request.config.getoption("--qa-artifacts-dir"))
    if not root.is_absolute():
        root = request.config.rootpath / root
    name = re.sub(r"[^\w.-]+", "_", request.node.name)[:80]
    digest = hashlib.sha256(request.node.nodeid.encode("utf-8")).hexdigest()[:12]
    return root / f"{name}-{digest}"
