"""Контракт диагностического файла для обмена между расширениями.

Источник сохраняет файл, а подключённые отчётчики получают его описание.
Контракт не зависит от pytest, Playwright или Allure.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DiagnosticArtifact:
    """Описание сохранённого диагностического файла."""

    path: Path
    name: str
    media_type: str
    extension: str
