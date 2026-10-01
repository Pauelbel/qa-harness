"""Переиспользуемые проверки уже полученных OData-ответов.

Зачем нужен файл:
    ``OdataAssertions`` проверяет типовые правила протокола: схему элементов,
    результаты ``$select`` и ``$filter``, пагинацию, сортировку, ``$count`` и
    ``$expand``. Модуль ничего не отправляет по сети и не знает эндпоинтов проекта.

Как использовать:
    Получите JSON проектным API-клиентом, извлеките ``value`` и вызовите нужные
    статические проверки.

    >>> payload = response.json()
    >>> items = payload["value"]
    >>> OdataAssertions.response_not_empty(items)
    >>> OdataAssertions.top_limit(items, 10)

Проверки используют ``pytest-check``, поэтому несколько нарушений могут быть
собраны в одном тесте без остановки после первого несовпадения.
"""

import pytest_check as check
from typing import List, Optional, Any, Union
from pydantic import BaseModel, ValidationError
from datetime import date, datetime


class OdataAssertions:
    """
    Универсальные статические проверки для OData-ответов.
    Подходит для любых эндпоинтов.
    Не выполняет HTTP-запросов — работает только с уже полученными данными.
    """

    # --- Базовые проверки ---

    @staticmethod
    def response_not_empty(data: list, msg: str = "Ответ содержит пустой массив 'value'"):
        """Проверяет, что массив value содержит хотя бы один элемент."""
        check.is_true(len(data) > 0, msg)

    @staticmethod
    def schema(items: List[dict], dto_model: type[BaseModel]):
        """Валидирует каждый элемент списка через Pydantic-модель."""
        for item in items:
            try:
                dto_model(**item)
            except ValidationError as e:
                check.is_true(False, f"Ошибка валидации схемы: {e.json()}")

    # --- $select ---

    @staticmethod
    def select_property(items: List[dict], property_name: str):
        """Проверяет, что среди записей есть хотя бы одно непустое значение указанного поля."""
        has_valid = any(
            item.get(property_name) is not None and item.get(property_name) != ""
            for item in items
        )
        check.is_true(
            has_valid,
            f"По фильтру $select={property_name} нет ни одного непустого значения"
        )

    @staticmethod
    def select_strict(
        items: List[dict],
        allowed_fields: List[str],
        system_fields: Optional[List[str]] = None
    ):
        """
        Строгая проверка $select: убеждается, что в каждой записи нет лишних полей.
        Разрешает системные поля OData (@odata.id, @odata.etag и т.п.).
        """
        if system_fields is None:
            system_fields = ["@odata.id", "@odata.etag", "@odata.editLink"]
        allowed = set(allowed_fields + system_fields)

        for item in items:
            extra = set(item.keys()) - allowed
            check.is_true(
                len(extra) == 0,
                f"При $select найдены лишние поля: {extra}. Ожидались только: {allowed_fields}"
            )

    # --- $filter (универсальные операторы) ---

    @staticmethod
    def filter_eq(items: List[dict], field: str, expected: Any):
        """Проверяет, что значение field во всех записях равно expected."""
        for item in items:
            actual = item.get(field)
            check.equal(
                actual, expected,
                f"Запись не соответствует фильтру {field} eq '{expected}'. "
                f"Ожидалось: {expected}, получено: {actual}"
            )

    @staticmethod
    def filter_ne(items: List[dict], field: str, unexpected: Any):
        """Проверяет, что значение field во всех записях НЕ равно unexpected."""
        for item in items:
            actual = item.get(field)
            check.not_equal(
                actual, unexpected,
                f"Запись не соответствует фильтру {field} ne '{unexpected}'. "
                f"Получено запрещённое значение: {actual}"
            )

    @staticmethod
    def filter_contains(items: List[dict], field: str, substring: str):
        """Проверяет, что строковое поле содержит substring (case-sensitive)."""
        for item in items:
            actual = item.get(field) or ""
            check.is_true(
                substring in actual,
                f"Поле {field}='{actual}' не содержит подстроку '{substring}'"
            )

    @staticmethod
    def filter_date_range(
        items: List[dict],
        field: str,
        start: Union[date, datetime, str],
        end: Union[date, datetime, str],
        date_format: str = "%Y-%m-%d"
    ):
        """
        Проверяет, что значение поля-даты находится в диапазоне [start, end].
        Например, для фильтра ``date ge 2026-01-01 and date le 2026-01-31``.
        """
        def _to_date(val):
            if isinstance(val, str):
                return datetime.strptime(val, date_format).date()
            if isinstance(val, datetime):
                return val.date()
            return val

        start_d = _to_date(start)
        end_d = _to_date(end)

        for item in items:
            raw = item.get(field)
            if raw is None:
                check.is_true(False, f"Поле {field} отсутствует для проверки диапазона дат")
                continue

            if isinstance(raw, str):
                try:
                    item_date = datetime.fromisoformat(raw.replace('Z', '+00:00')).date()
                except ValueError:
                    item_date = datetime.strptime(raw, date_format).date()
            elif isinstance(raw, datetime):
                item_date = raw.date()
            elif isinstance(raw, date):
                item_date = raw
            else:
                check.is_true(False, f"Поле {field} имеет неподдерживаемый тип: {type(raw)}")
                continue

            check.is_true(
                start_d <= item_date <= end_d,
                f"Дата {item_date} вне диапазона [{start_d}, {end_d}]"
            )

    # --- $top / $skip / $count ---

    @staticmethod
    def top_limit(items: List[dict], limit: int):
        """Проверяет, что количество записей не превышает заданный лимит."""
        check.is_true(
            len(items) <= limit,
            f"Вернулись {len(items)} записей, ожидалось не более {limit}"
        )

    @staticmethod
    def skip_consistency(
        first_page: List[dict],
        skipped_page: List[dict],
        skip: int,
        key_field: str = "Id",
    ):
        """Сравнивает first_page[skip] со skipped_page[0] по ключевому полю key_field."""
        if len(first_page) > skip and skipped_page:
            check.equal(
                first_page[skip][key_field],
                skipped_page[0][key_field],
                f"Первая запись после skip={skip} не совпадает с ожидаемой"
            )

    @staticmethod
    def count_present(response_data: dict):
        """Проверяет наличие @odata.count, его тип int и что len(value) <= count."""
        total_count = response_data.get("@odata.count")
        items = response_data.get("value", [])

        check.is_not_none(total_count, "Поле @odata.count отсутствует в ответе")
        if total_count is not None:
            check.is_instance(total_count, int, f"@odata.count имеет тип {type(total_count)}, ожидался int")
            check.is_true(
                len(items) <= total_count,
                "Количество записей в value превышает @odata.count"
            )

    # --- $expand ---

    @staticmethod
    def expand_field(
        items: List[dict],
        field: str,
        expected_type: Optional[type] = None
    ):
        """
        Проверяет наличие поля навигации после $expand.
        Опционально проверяет тип: list для коллекций, dict для одиночных ссылок.
        """
        for item in items:
            value = item.get(field)
            check.is_not_none(
                value,
                f"Поле {field} отсутствует в ответе при $expand={field}"
            )
            if expected_type is not None and value is not None:
                check.is_instance(
                    value, expected_type,
                    f"Поле {field} имеет тип {type(value)}, ожидался {expected_type}"
                )

    # --- $orderby ---

    @staticmethod
    def orderby(items: List[dict], field: str, reverse: bool = False):
        """
        Проверяет сортировку по одному полю.
        Внимание: если бэкенд использует locale-aware или case-insensitive сортировку,
        порядок может отличаться от Python sorted(). В этом случае скорректируй expected.
        """
        values = [item.get(field) or "" for item in items]
        expected = sorted(values, reverse=reverse)
        direction = "desc" if reverse else "asc"
        check.equal(
            values, expected,
            f"Записи не отсортированы по {field} {direction}"
        )
