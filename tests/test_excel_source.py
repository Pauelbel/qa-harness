"""Изолированные проверки источника Excel-файлов."""

from pathlib import Path

import allure
import pytest

from qa_core.sources.excel import ExcelSource


class StubResponse:
    def __init__(self, content: bytes, content_disposition: str = "") -> None:
        self.content = content
        self.headers = {"Content-Disposition": content_disposition}
        self.status_checked = False

    def raise_for_status(self) -> None:
        self.status_checked = True


@allure.epic("Backend")
@allure.title("ExcelSource принимает существующий файл")
def test_excel_source_uses_existing_file(tmp_path: Path) -> None:
    report_path = tmp_path / "report.xlsx"
    report_path.write_bytes(b"excel")

    with allure.step("Подготовить Excel из локального файла"):
        report = ExcelSource.from_path(report_path)

    with allure.step("Проверить путь и имя"):
        assert report.path == report_path
        assert report.original_filename == "report.xlsx"


@allure.epic("Backend")
@allure.title("ExcelSource сохраняет HTTP-ответ")
def test_excel_source_saves_http_response(tmp_path: Path) -> None:
    response = StubResponse(
        b"excel",
        "attachment; filename*=UTF-8''report%20from%20api.xlsx",
    )

    with allure.step("Сохранить Excel из HTTP-ответа"):
        report = ExcelSource.from_response(
            response,
            tmp_path / "downloads" / "report.xlsx",
        )

    with allure.step("Проверить содержимое и исходное имя"):
        assert response.status_checked is True
        assert report.path.read_bytes() == b"excel"
        assert report.original_filename == "report from api.xlsx"


@allure.epic("Backend")
@allure.title("ExcelSource отклоняет пустое содержимое")
def test_excel_source_rejects_empty_content(tmp_path: Path) -> None:
    with allure.step("Проверить ошибку для пустых байтов"):
        with pytest.raises(ValueError, match="пустого содержимого"):
            ExcelSource.from_bytes(b"", tmp_path / "report.xlsx")
