"""Пример: скачать Excel-отчёт и проверить его."""

from pathlib import Path

import allure
import pandas as pd
import pytest

from qa_core.checks.excel import ExcelDataQualityChecker
from qa_core.clients.http import BaseHttpClient
from qa_core.sources.excel import ExcelSource


@allure.epic("Примеры")
@allure.title("Excel: скачать отчёт и проверить структуру и значения")
def test_downloaded_report(demo_url: str, tmp_path: Path) -> None:
    with allure.step("Скачать отчёт"):
        with BaseHttpClient() as http:
            response = http.get(f"{demo_url}/report")
        report = ExcelSource.from_response(response, tmp_path / "report.xlsx")

    with allure.step("Проверить структуру"):
        checker = ExcelDataQualityChecker(report.path)
        checker.check_filename(
            actual_name=report.original_filename,
            expected_suffix=".xlsx",
        )
        checker.check_columns(["ФИО", "Дата", "Часы"], strict_order=True)

    with allure.step("Проверить значения"):
        checker.check_required(["ФИО", "Дата"])
        checker.check_date("Дата")
        checker.check_is_numeric("Часы")
        checker.check_range("Часы", min_value=0, min_inclusive=False, max_value=24)

    with allure.step("Завершить проверку"):
        checker.assert_valid()


@allure.epic("Примеры")
@allure.title("Excel: файл с ошибками даёт одно сообщение со всеми нарушениями")
def test_errors_are_collected(tmp_path: Path) -> None:
    broken = tmp_path / "broken.xlsx"
    pd.DataFrame(
        {"ФИО": ["Иванов Иван", None], "Дата": ["01.09.2026", "не дата"], "Часы": [8, -1]}
    ).to_excel(broken, index=False, engine="openpyxl")

    checker = ExcelDataQualityChecker(ExcelSource.from_path(broken).path)
    checker.check_required(["ФИО"])
    checker.check_date("Дата")
    checker.check_range("Часы", min_value=0)

    with pytest.raises(AssertionError) as error:
        checker.assert_valid()

    allure.attach(str(error.value), name="Текст ошибки", attachment_type=allure.attachment_type.TEXT)
    assert "ФИО" in str(error.value)
    assert "Дата" in str(error.value)
    assert "Часы" in str(error.value)
