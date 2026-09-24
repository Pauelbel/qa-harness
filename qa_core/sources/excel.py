"""Подготовка Excel-файла перед передачей в checker.

Зачем нужен файл:
    ``ExcelSource`` отделяет способ получения отчёта от его проверки. Источником
    может быть уже существующий файл, набор байтов или HTTP-ответ.

Как использовать:
    >>> response = report_api.download_report()
    >>> report = ExcelSource.from_response(response, tmp_path / "report.xlsx")
    >>> ExcelDataQualityChecker(report.path).check_required(["ФИО"]).assert_valid()

Модуль не знает URL, авторизацию и эндпоинты конкретной системы. HTTP-запрос
выполняет клиент проекта, а источник сохраняет файл и возвращает его
путь вместе с исходным именем.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol, Union
from urllib.parse import unquote


PathLike = Union[str, Path]


@dataclass(frozen=True)
class ExcelFile:
    """Excel-файл, подготовленный для проверок.

    ``path`` указывает на локальный файл, а ``original_filename`` хранит
    имя, переданное сервером в ``Content-Disposition``.
    """

    path: Path
    original_filename: str | None = None


class BinaryHttpResponse(Protocol):
    """Минимальный контракт HTTP-ответа, необходимый источнику."""

    content: bytes
    headers: Mapping[str, str]

    def raise_for_status(self) -> None: ...


class ExcelSource:
    """Приводит разные способы получения Excel к единому ``ExcelFile``."""

    @staticmethod
    def from_path(file_path: PathLike) -> ExcelFile:
        """Возвращает существующий файл или сообщает, что он не найден."""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Excel-файл не найден: {path}")
        return ExcelFile(path=path, original_filename=path.name)

    @staticmethod
    def from_bytes(
        content: bytes,
        destination: PathLike,
        original_filename: str | None = None,
    ) -> ExcelFile:
        """Сохраняет байты и возвращает описание Excel-файла."""
        if not content:
            raise ValueError("Нельзя создать Excel-файл из пустого содержимого")

        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return ExcelFile(path=path, original_filename=original_filename)

    @classmethod
    def from_response(
        cls,
        response: BinaryHttpResponse,
        destination: PathLike,
    ) -> ExcelFile:
        """Проверяет HTTP-ответ и сохраняет полученный Excel."""
        response.raise_for_status()
        return cls.from_bytes(
            response.content,
            destination,
            original_filename=cls._extract_filename(
                response.headers.get("Content-Disposition", "")
            ),
        )

    @staticmethod
    def _extract_filename(content_disposition: str) -> str | None:
        """Извлекает имя файла из HTTP-заголовка ``Content-Disposition``."""
        encoded = re.search(
            r"filename\*=UTF-8''([^;]+)",
            content_disposition,
            re.IGNORECASE,
        )
        if encoded:
            return unquote(encoded.group(1).strip())

        plain = re.search(
            r'filename=["\']?([^"\';]+)',
            content_disposition,
            re.IGNORECASE,
        )
        if plain:
            return plain.group(1).strip().strip('"\'')
        return None
