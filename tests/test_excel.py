"""Проверки Excel-checker на маленьких временных отчётах."""

from pathlib import Path

import allure
import pandas as pd
import pytest

from qa_core.checks.excel import ExcelDataQualityChecker


@allure.epic("Backend")
@allure.title("Валидный Excel-отчёт проходит проверки")
def test_excel_checker_accepts_valid_report(tmp_path: Path) -> None:
    report_path = tmp_path / "valid.xlsx"
    pd.DataFrame(
        {"ФИО": ["Иванов"], "Дата": ["23.09.2026"]}
    ).to_excel(report_path, index=False)

    with allure.step("Проверить структуру и значения Excel"):
        checker = ExcelDataQualityChecker(report_path)
        assert checker.get_row_count() == 1
        checker.check_columns(["ФИО", "Дата"], strict_order=True)
        checker.check_required(["ФИО", "Дата"])
        checker.check_date("Дата")
        checker.assert_valid()


@allure.epic("Backend")
@allure.title("Excel-checker сообщает о пустом обязательном поле")
def test_excel_checker_reports_empty_required_cell(tmp_path: Path) -> None:
    report_path = tmp_path / "invalid.xlsx"
    pd.DataFrame(
        {
            "ФИО": [None, "Петров"],
            "Дата": ["23.09.2026", "24.09.2026"],
        }
    ).to_excel(
        report_path,
        index=False,
    )

    with allure.step("Проверить обязательное поле"):
        checker = ExcelDataQualityChecker(report_path)
        checker.check_required(["ФИО"])

    with allure.step("Проверить сообщение об ошибке"):
        with pytest.raises(AssertionError, match="ФИО"):
            checker.assert_valid()


@allure.epic("Backend")
@allure.title("Текст «None» и «nan» в ячейке остаётся значением, а не пустотой")
def test_excel_checker_keeps_none_and_nan_text(tmp_path: Path) -> None:
    report_path = tmp_path / "none_text.xlsx"
    pd.DataFrame({"Статус": ["None", "nan", "Готово"]}).to_excel(report_path, index=False)

    checker = ExcelDataQualityChecker(report_path)

    assert checker.df["Статус"].tolist() == ["None", "nan", "Готово"]
    checker.check_required(["Статус"])
    checker.assert_valid()


@allure.epic("Backend")
@allure.title("Пробелы по краям обрезаются, а ячейка из пробелов считается пустой")
def test_excel_checker_trims_text_and_detects_blank(tmp_path: Path) -> None:
    report_path = tmp_path / "spaces.xlsx"
    pd.DataFrame({"ФИО": ["  Иванов  ", "   ", None, "Петров"]}).to_excel(report_path, index=False)

    checker = ExcelDataQualityChecker(report_path)

    assert checker.df["ФИО"].iloc[0] == "Иванов"
    assert checker.df["ФИО"].isna().tolist() == [False, True, True, False]
    checker.check_required(["ФИО"])
    with pytest.raises(AssertionError):
        checker.assert_valid()
