"""Проверки OData-assertions на обычных Python-структурах."""

import allure

from qa_core.checks import odata
from qa_core.checks.odata import OdataAssertions


@allure.epic("Backend")
@allure.title("Валидный OData-ответ проходит базовые проверки")
def test_valid_odata_items_pass_common_checks() -> None:
    items = [{"id": 1, "status": "new"}, {"id": 2, "status": "new"}]

    with allure.step("Проверить OData-массив"):
        OdataAssertions.response_not_empty(items)
        OdataAssertions.filter_eq(items, "status", "new")
        OdataAssertions.top_limit(items, 2)
        OdataAssertions.orderby(items, "id")


@allure.epic("Backend")
@allure.title("Пустой OData-ответ фиксируется как ошибка")
def test_empty_response_is_reported(monkeypatch) -> None:
    calls: list[tuple[bool, str]] = []
    monkeypatch.setattr(
        odata.check,
        "is_true",
        lambda condition, message: calls.append((condition, message)),
    )

    with allure.step("Проверить пустой OData-массив"):
        OdataAssertions.response_not_empty([])

    with allure.step("Проверить текст ошибки"):
        assert calls == [(False, "Ответ содержит пустой массив 'value'")]
