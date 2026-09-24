"""Изолированные проверки источника Excel-файлов."""

from pathlib import Path

import pytest

from qa_core.sources.excel import ExcelSource


class StubResponse:
    def __init__(self, content: bytes, content_disposition: str = "") -> None:
        self.content = content
        self.headers = {"Content-Disposition": content_disposition}
        self.status_checked = False

    def raise_for_status(self) -> None:
        self.status_checked = True


def test_excel_source_uses_existing_file(tmp_path: Path) -> None:
    report_path = tmp_path / "report.xlsx"
    report_path.write_bytes(b"excel")

    report = ExcelSource.from_path(report_path)

    assert report.path == report_path
    assert report.original_filename == "report.xlsx"


def test_excel_source_saves_http_response(tmp_path: Path) -> None:
    response = StubResponse(
        b"excel",
        "attachment; filename*=UTF-8''report%20from%20api.xlsx",
    )

    report = ExcelSource.from_response(
        response,
        tmp_path / "downloads" / "report.xlsx",
    )

    assert response.status_checked is True
    assert report.path.read_bytes() == b"excel"
    assert report.original_filename == "report from api.xlsx"


def test_excel_source_rejects_empty_content(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="пустого содержимого"):
        ExcelSource.from_bytes(b"", tmp_path / "report.xlsx")
