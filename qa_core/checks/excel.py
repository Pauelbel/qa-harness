"""Набор последовательных проверок качества Excel-отчётов.

Зачем нужен файл:
    ``ExcelDataQualityChecker`` загружает таблицу, выполняет независимые проверки
    колонок и значений и накапливает все найденные ошибки. Названия колонок и
    правила конкретного отчёта остаются в тесте, а не в ядре.

Как использовать:
    Создайте checker для файла, соберите цепочку необходимых проверок и завершите
    её вызовом ``assert_valid``.

    >>> checker = ExcelDataQualityChecker("report.xlsx")
    >>> checker.check_columns(["ФИО", "Дата"]).check_required(["ФИО"])
    >>> checker.check_date("Дата").assert_valid()

Если найдены нарушения, ``assert_valid`` формирует одно читаемое сообщение со
строками и примерами значений вместо остановки на первой ошибке.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence, Union

import pandas as pd

# =============================================================================
# 1. Модель ошибки
# =============================================================================
@dataclass(frozen=True)
class CheckError:
    """Одна найденная ошибка в конкретной ячейке Excel-отчёта.

    Атрибуты:
        row: Номер строки в Excel (1-based, заголовок = строка 1).
        column: Имя колонки, в которой найдена ошибка.
        message: Человекочитаемое описание проблемы.
        value: Фактическое значение ячейки, если ошибка относится к строке отчёта.

    Пример:
        >>> error = CheckError(row=5, column="Дата списания", message="не парсится")
        >>> str(error)
        "[ROW 5] 'Дата списания' → не парсится"
    """
    row: int
    column: str
    message: str
    value: Any = None

    def __str__(self) -> str:
        return f"[ROW {self.row}] '{self.column}' → {self.message}"



# ===========================================================================================================================
# 2. Ядро валидации Excel
# ===========================================================================================================================
class ExcelDataQualityChecker:
    """Универсальный валидатор Excel-отчётов.

    Загружает файл, предобрабатывает строковые ячейки и накапливает ошибки.
    Все параметры проверок передаются извне — хардкода колонок нет.

    Пример использования в тесте:
        >>> checker = ExcelDataQualityChecker("report.xlsx")
        >>> checker.check_columns(["Должность", "ФИО"]).check_required(["Должность"])
        >>> checker.assert_valid()  # выбросит AssertionError, если есть ошибки
    """

    def __init__(self, file_path: Union[str, Path]) -> None:
        self.path = Path(file_path)
        self.df: pd.DataFrame = self._load()
        self._errors: List[CheckError] = []

    # ------------------------------------------------------------------ #
    # Внутренние утилиты
    # ------------------------------------------------------------------ #
    def _load(self) -> pd.DataFrame:
        """Загружает xlsx и выполняет базовую очистку строковых ячеек.

        Что делает:
            - Читает Excel через ``openpyxl``.
            - Чистит названия колонок (strip).
            - Заменяет ``NaN``, ``"nan"``, ``"None"``, ``"NaT"`` на ``pd.NA``.
            - Обрезает пробелы по краям во всех строковых ячейках.
        """
        df = pd.read_excel(self.path, engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]

        # Заменяем float NaN на pd.NA для всего DataFrame
        df = df.replace(float('nan'), pd.NA)

        for col in df.columns:
            # Если колонка object/string — чистим строки
            if df[col].dtype == 'object':
                df[col] = (
                    df[col]
                    .astype(str)
                    .replace("nan", "")
                    .replace("None", "")
                    .replace("NaT", "")
                    .replace("<NA>", "")
                    .str.strip()
                    .replace("", pd.NA)
                )
            else:
                # Для числовых/других типов — просто NaN -> pd.NA
                df[col] = df[col].replace(float('nan'), pd.NA)

        return df

    def _is_empty(self, series: pd.Series) -> pd.Series:
        """Возвращает булеву маску: True там, где значение пустое.

        Пустыми считаются: ``pd.NA``, ``None``, ``NaN``, ``""``, 
        строки из пробелов, ``"nan"``, ``"None"``, ``"NaT"``, ``"<NA>"``.
        """
        # Проверяем isna() для всех типов (ловит pd.NA, np.nan, None)
        is_na = series.isna()

        # Для строковых — дополнительно проверяем строковые представления
        if series.dtype == 'object':
            str_vals = series.astype(str).str.strip()
            is_empty_str = str_vals.isin(["", "nan", "None", "NaT", "<NA>"])
            return is_na | is_empty_str

        return is_na

    def _add(self, mask: pd.Series, column: str, message: str) -> None:
        """По булевой маске создаёт ``CheckError`` для каждой строки.

        Параметры:
            mask: Булева Series, где True = ошибка в этой строке.
            column: Имя колонки для сообщения об ошибке.
            message: Текст ошибки.
        """
        for idx in self.df[mask].index:
            self._errors.append(
                CheckError(
                    row=idx + 2,
                    column=column,
                    message=message,
                    value=self.df.at[idx, column],
                )
            )

    @staticmethod
    def _format_error_value(value: Any, max_length: int = 120) -> str:
        """Возвращает короткое и читаемое представление значения для assert."""
        if value is None or (not isinstance(value, (list, tuple, dict, set)) and pd.isna(value)):
            return "<пусто>"

        text = str(value).replace("\n", " ").replace("\r", " ")
        if len(text) > max_length:
            text = f"{text[:max_length]}…"
        return f"«{text}»"

    # ------------------------------------------------------------------ #
    # Публичные методы проверки
    # ------------------------------------------------------------------ #
    def check_columns(
        self,
        expected: Sequence[str],
        strict_order: bool = False,
    ) -> ExcelDataQualityChecker:
        """Проверяет наличие, отсутствие лишних и порядок столбцов.

        Что проверяет:
            - Все ли столбцы из ``expected`` присутствуют в файле.
            - Есть ли столбцы, которых нет в ``expected``.
            - При ``strict_order=True`` — идут ли они в том же порядке.

        Параметры:
            expected: Список имён столбцов, которые должны быть в файле.
            strict_order: Если ``True``, проверяет также порядок следования.

        Пример в тесте:
            >>> checker.check_columns(
            ...     ["Должность", "ФИО", "Дата списания"],
            ...     strict_order=True,
            ... )
        """
        actual = list(self.df.columns)
        missing = [c for c in expected if c not in actual]
        extra = [c for c in actual if c not in expected]

        if missing:
            self._errors.append(
                CheckError(row=1, column="STRUCTURE",
                           message=f"Отсутствуют столбцы: {missing}")
            )
        if extra:
            self._errors.append(
                CheckError(row=1, column="STRUCTURE",
                           message=f"Лишние столбцы: {extra}")
            )
        if strict_order:
            actual_common = [c for c in actual if c in expected]
            if list(expected) != actual_common:
                self._errors.append(
                    CheckError(row=1, column="STRUCTURE",
                               message="Порядок столбцов не совпадает с ожидаемым")
                )
        return self

    def check_required(self, columns: Sequence[str]) -> ExcelDataQualityChecker:
        """Проверяет, что указанные столбцы заполнены во всех строках.

        Что проверяет:
            Для каждой строки и каждого столбца из ``columns`` проверяет,
            что значение не пустое (не ``NaN``, не пустая строка, не ``"nan"``).

        Параметры:
            columns: Список имён столбцов для проверки.

        Пример в тесте:
            >>> checker.check_required([
            ...     "Должность", "ФИО", "Дата списания",
            ...     "Затраченное время в минутах", "Заказ/название",
            ... ])
        """
        for col in columns:
            if col not in self.df.columns:
                self._errors.append(
                    CheckError(row=1, column=col,
                               message="Столбец отсутствует — проверка невозможна")
                )
                continue
            empty = self._is_empty(self.df[col])
            self._add(empty, col, "обязательное поле должно быть заполнено")
        return self

    def check_date(self, column: str, fmt: str = "%d.%m.%Y") -> ExcelDataQualityChecker:
        """Проверяет, что столбец парсится как дата в заданном формате.

        Что проверяет:
            Каждое непустое значение должно успешно конвертироваться
            в ``datetime`` по шаблону ``fmt`` (по умолчанию ``DD.MM.YYYY``).

        Параметры:
            column: Имя столбца.
            fmt: Строка формата для ``pd.to_datetime``.

        Пример в тесте:
            >>> checker.check_date("Дата списания", fmt="%d.%m.%Y")
        """
        if column not in self.df.columns:
            self._errors.append(
                CheckError(row=1, column=column, message="Столбец не найден")
            )
            return self

        parsed = pd.to_datetime(self.df[column], format=fmt, errors="coerce")
        bad = self.df[column].notna() & parsed.isna()
        self._add(bad, column, f"дата должна соответствовать формату {fmt}")
        return self

    def check_date_period(
        self,
        column: str,
        fmt: str = "%d.%m.%Y",
    ) -> ExcelDataQualityChecker:
        """Проверяет интервал из двух дат, разделённых дефисом.

        Пустые ячейки не считаются ошибкой. Для заполненной ячейки обе даты
        должны быть корректны и соответствовать заданному формату.

        Параметры:
            column: Название колонки с периодом. Например, ``"Период"``.
            fmt: Формат каждой даты. По умолчанию ``"%d.%m.%Y"``, то есть
                дата вида ``31.12.2026``.
        """
        if column not in self.df.columns:
            self._errors.append(
                CheckError(row=1, column=column, message="Столбец не найден")
            )
            return self

        series = self.df[column]
        filled = ~self._is_empty(series)
        parts = series.astype(str).str.extract(
            r"^\s*(.+?)\s*[-–—]\s*(.+?)\s*$"
        )
        parsed_start = pd.to_datetime(parts[0], format=fmt, errors="coerce")
        parsed_end = pd.to_datetime(parts[1], format=fmt, errors="coerce")
        bad = filled & (parts[0].isna() | parts[1].isna() | parsed_start.isna() | parsed_end.isna())
        self._add(
            bad,
            column,
            f"должно содержать две корректные даты формата {fmt}, разделённые дефисом",
        )
        return self

    def check_is_numeric(self, column: str) -> ExcelDataQualityChecker:
        """Проверяет, что каждое заполненное значение является числом.

        Параметры:
            column: Название числовой колонки. Например, ``"Стоимость"``.
        """
        if column not in self.df.columns:
            self._errors.append(
                CheckError(row=1, column=column, message="Столбец не найден")
            )
            return self

        numeric = pd.to_numeric(self.df[column], errors="coerce")
        bad = ~self._is_empty(self.df[column]) & numeric.isna()
        self._add(bad, column, "значение должно быть числом")
        return self

    def check_integer(self, column: str) -> ExcelDataQualityChecker:
        """Проверяет, что числовые значения не содержат дробной части.

        Параметры:
            column: Название колонки с целыми числами. Например,
                ``"Затраченное время в минутах"``.
        """
        if column not in self.df.columns:
            self._errors.append(
                CheckError(row=1, column=column, message="Столбец не найден")
            )
            return self

        numeric = pd.to_numeric(self.df[column], errors="coerce")
        self._add(
            numeric.notna() & (numeric != numeric.round()),
            column,
            "должно быть целым числом",
        )
        return self

    def check_range(
        self,
        column: str,
        min_value: Optional[float] = None,
        min_inclusive: bool = True,
        max_value: Optional[float] = None,
        max_inclusive: bool = True,
    ) -> ExcelDataQualityChecker:
        """Проверяет попадание числовых значений в заданный диапазон.

        Проверка типа выполняется отдельно через :meth:`check_is_numeric`.
        Границы можно сделать строгими: ``min_inclusive=False`` задаёт
        условие «больше», а ``max_inclusive=False`` — условие «меньше».

        Параметры:
            column: Название проверяемой колонки отчёта.
            min_value: Минимально допустимое значение. Например, ``0``.
            min_inclusive: Разрешён ли минимум. ``True`` — ноль допустим,
                ``False`` — значение должно быть строго больше нуля.
            max_value: Максимально допустимое значение. Например, ``100``.
            max_inclusive: Разрешён ли максимум. ``True`` — 100 допустимо,
                ``False`` — значение должно быть строго меньше 100.
        """
        if column not in self.df.columns:
            self._errors.append(
                CheckError(row=1, column=column, message="Столбец не найден")
            )
            return self

        if min_value is None and max_value is None:
            raise ValueError("Для проверки диапазона нужна хотя бы одна граница")
        if min_value is not None and max_value is not None and min_value > max_value:
            raise ValueError("Минимальная граница не может быть больше максимальной")

        numeric = pd.to_numeric(self.df[column], errors="coerce")
        valid = numeric.notna()
        rules = []

        if min_value is not None:
            valid &= numeric >= min_value if min_inclusive else numeric > min_value
            rules.append(
                f"значение должно быть не меньше {min_value}"
                if min_inclusive
                else f"значение должно быть строго больше {min_value}"
            )

        if max_value is not None:
            valid &= numeric <= max_value if max_inclusive else numeric < max_value
            rules.append(
                f"значение должно быть не больше {max_value}"
                if max_inclusive
                else f"значение должно быть строго меньше {max_value}"
            )

        self._add(numeric.notna() & ~valid, column, " и ".join(rules))
        return self

    def check_enum(
        self,
        column: str,
        allowed: Iterable[str],
        case_sensitive: bool = True,
    ) -> ExcelDataQualityChecker:
        """Проверяет, что значения столбца входят в разрешённый список.

        Что проверяет:
            Каждое непустое значение должно быть строго из множества ``allowed``.
            Пустые ячейки (``NaN``) игнорируются.

        Параметры:
            column: Имя столбца.
            allowed: Допустимые значения.
            case_sensitive: Учитывать ли регистр (по умолчанию ``True``).

        Пример в тесте:
            >>> checker.check_enum("Ночное списание", allowed=["Да", "Нет"])
            >>> checker.check_enum("Нерабочее время", allowed=["Да", "Нет"])
        """
        if column not in self.df.columns:
            self._errors.append(
                CheckError(row=1, column=column, message="Столбец не найден")
            )
            return self

        allowed_set = set(allowed)
        series = self.df[column]

        if not case_sensitive:
            allowed_set = {v.lower() for v in allowed_set}
            series = series.astype(str).str.lower()
            mask = self.df[column].notna() & ~series.isin(allowed_set)
        else:
            mask = self.df[column].notna() & ~self.df[column].isin(allowed_set)

        self._add(mask, column, f"значение должно входить в допустимый список: {list(allowed)}")
        return self

    def check_regex(
        self,
        column: str,
        pattern: str,
        description: str,
    ) -> ExcelDataQualityChecker:
        r"""Проверяет непустые значения колонки по регулярному выражению.

        Параметры:
            column: Название проверяемой колонки.
            pattern: Регулярное выражение полного значения. Например,
                ``r"\d+\.\d{3}"`` для кода вида ``123.456``.
            description: Простое описание правила, которое будет показано в
                ошибке. Например, ``"должно содержать цифры.три цифры"``.
        """
        if column not in self.df.columns:
            self._errors.append(
                CheckError(row=1, column=column, message="Столбец не найден")
            )
            return self

        series = self.df[column]
        filled = ~self._is_empty(series)
        cleaned_series = series.astype(str).str.strip()
        matches = cleaned_series.str.fullmatch(pattern, na=False)
        self._add(filled & ~matches, column, description)
        return self

    def check_text(self, column: str) -> ExcelDataQualityChecker:
        """Проверяет, что непустые значения колонки являются текстом.

        Параметры:
            column: Название текстовой колонки. Например, ``"Описание"``.
        """
        if column not in self.df.columns:
            self._errors.append(
                CheckError(row=1, column=column, message="Столбец не найден")
            )
            return self

        series = self.df[column]
        filled = ~self._is_empty(series)
        is_text = series.map(lambda value: isinstance(value, str))
        self._add(filled & ~is_text, column, "должно быть текстовым значением")
        return self

    def check_decimal_places(
        self,
        column: str,
        max_decimal_places: int,
    ) -> ExcelDataQualityChecker:
        """Проверяет точность числовых значений.

        Параметры:
            column: Название числовой колонки.
            max_decimal_places: Максимальное число знаков после запятой или
                точки. Например, ``2`` допускает ``10,50`` и ``10.5``.
        """
        if column not in self.df.columns:
            self._errors.append(
                CheckError(row=1, column=column, message="Столбец не найден")
            )
            return self

        numeric = pd.to_numeric(self.df[column], errors="coerce")
        difference = (numeric - numeric.round(max_decimal_places)).abs()
        bad = numeric.notna() & (difference > 1e-9)
        self._add(
            bad,
            column,
            f"число должно содержать не более {max_decimal_places} знаков после запятой",
        )
        return self

    def check_percentage(
        self,
        column: str,
        max_decimal_places: int = 2,
        min_value: Optional[float] = 0,
        min_inclusive: bool = True,
        max_value: Optional[float] = None,
        max_inclusive: bool = True,
    ) -> ExcelDataQualityChecker:
        """Проверяет процент со знаком ``%`` и заданными границами.

        Пустые ячейки игнорируются. Допускаются точка или запятая в качестве
        разделителя дробной части и не более указанного числа знаков после него.
        По умолчанию допускается ноль и положительные значения.

        Параметры:
            column: Название проверяемой колонки отчёта.
            max_decimal_places: Максимальное число знаков после запятой или
                точки. Например, ``2`` допускает ``25,50%`` и ``25.5%``.
            min_value: Минимально допустимое значение процента. По умолчанию
                ``0``, поэтому отрицательные проценты не допускаются.
            min_inclusive: Разрешён ли минимум. ``True`` — ``0%`` допустим,
                ``False`` — процент должен быть строго больше нуля.
            max_value: Максимально допустимое значение процента. Если не
                указан, верхней границы нет.
            max_inclusive: Разрешён ли максимум. ``True`` — граница допустима,
                ``False`` — процент должен быть строго меньше неё.
        """
        if column not in self.df.columns:
            self._errors.append(
                CheckError(row=1, column=column, message="Столбец не найден")
            )
            return self

        series = self.df[column]
        filled = ~self._is_empty(series)
        if min_value is not None and max_value is not None and min_value > max_value:
            raise ValueError("Минимальная граница не может быть больше максимальной")

        allow_negative = min_value is None or min_value < 0
        sign = r"-?" if allow_negative else ""
        pattern = rf"{sign}(?:0|[1-9]\d*)(?:[.,]\d{{1,{max_decimal_places}}})?%"
        matches = series.astype(str).str.fullmatch(pattern, na=False)
        numeric = pd.to_numeric(
            series.astype(str).str.rstrip("%").str.replace(",", ".", regex=False),
            errors="coerce",
        )
        valid = matches.copy()
        rules = []
        if min_value is not None:
            valid &= numeric >= min_value if min_inclusive else numeric > min_value
            rules.append(
                f"значение должно быть не меньше {min_value}"
                if min_inclusive
                else f"значение должно быть строго больше {min_value}"
            )
        if max_value is not None:
            valid &= numeric <= max_value if max_inclusive else numeric < max_value
            rules.append(
                f"значение должно быть не больше {max_value}"
                if max_inclusive
                else f"значение должно быть строго меньше {max_value}"
            )

        range_rule = " и ".join(rules) if rules else "значение может быть любого знака"
        self._add(
            filled & ~valid,
            column,
            f"процент должен иметь символ % и не более {max_decimal_places} знаков после разделителя; {range_rule}",
        )
        return self

    def check_cost_calculation(
        self,
        hours_col: str,
        rate_col: str,
        cost_col: str,
        tolerance: float = 0.01,
    ) -> ExcelDataQualityChecker:
        """Проверяет, что стоимость = часы × ставка.

        Что проверяет:
            Для каждой строки, где все три столбца заполнены,
            разница ``|фактическая стоимость − часы×ставка| ≤ tolerance``.
            Ожидаемое значение округляется до 2 знаков.

        Параметры:
            hours_col: Имя столбца с часами.
            rate_col: Имя столбца со стоимостью нормочаса.
            cost_col: Имя столбца с итоговой стоимостью.
            tolerance: Допустимая погрешность (по умолчанию 0.01).

        Пример в тесте:
            >>> checker.check_cost_calculation(
            ...     hours_col="Затраченное время в часах",
            ...     rate_col="Стоимость нормочаса",
            ...     cost_col="Стоимость",
            ...     tolerance=0.01,
            ... )
        """
        cols = [hours_col, rate_col, cost_col]
        if not all(c in self.df.columns for c in cols):
            miss = [c for c in cols if c not in self.df.columns]
            self._errors.append(
                CheckError(row=1, column="CALC",
                           message=f"Отсутствуют столбцы для проверки стоимости: {miss}")
            )
            return self

        hrs = pd.to_numeric(self.df[hours_col], errors="coerce")
        rate = pd.to_numeric(self.df[rate_col], errors="coerce")
        cost = pd.to_numeric(self.df[cost_col], errors="coerce")
        expected = (hrs * rate).round(2)
        bad = hrs.notna() & rate.notna() & cost.notna() & ((cost - expected).abs() > tolerance)
        self._add(
            bad, cost_col,
            f"стоимость должна быть равна «{hours_col}» × «{rate_col}» с погрешностью не более {tolerance}"
        )
        return self

    def get_fill_statistics(
        self,
        columns: Optional[Sequence[str]] = None,
    ) -> pd.DataFrame:
        """Возвращает статистику заполненности колонок без формирования ошибок.

        Параметры:
            columns: Колонки для статистики. Если не указаны, используются
                все колонки отчёта.

        Результат содержит названия колонок, число заполненных и пустых ячеек
        и процент заполненности.
        """
        cols_to_check = list(columns) if columns else list(self.df.columns)
        total_rows = len(self.df)
        if total_rows == 0:
            return pd.DataFrame(
                columns=["Колонка", "Заполнено", "Пусто", "Заполненность, %"]
            )

        statistics = []
        for col in cols_to_check:
            if col not in self.df.columns:
                continue

            empty_count = int(self._is_empty(self.df[col]).sum())
            filled_count = total_rows - empty_count
            statistics.append(
                {
                    "Колонка": col,
                    "Заполнено": filled_count,
                    "Пусто": empty_count,
                    "Заполненность, %": round(filled_count / total_rows * 100, 2),
                }
            )

        return pd.DataFrame(statistics)

    def check_no_fully_empty_columns(
        self,
        columns: Optional[Sequence[str]] = None,
        max_empty_percent: Optional[float] = None,
        max_errors_per_column: int = 1,
    ) -> ExcelDataQualityChecker:
        """Проверяет полностью пустые колонки или заданный порог пустоты.

        Без ``max_empty_percent`` фиксирует только колонки с заполненностью 0%.
        Параметр оставлен для ранее созданных проверок с порогом пустых значений.

        Параметры:
            columns: Колонки для проверки. Если не указаны, проверяются все.
            max_empty_percent: Допустимый процент пустых значений. Если не
                указан, ошибка возникает только для полностью пустой колонки.
            max_errors_per_column: Максимум сообщений об одной колонке за
                один запуск. Обычно достаточно ``1``.
        """
        cols_to_check = list(columns) if columns else list(self.df.columns)
        total_rows = len(self.df)
        if total_rows == 0:
            self._errors.append(
                CheckError(row=1, column="DATA", message="Отчёт не содержит строк")
            )
            return self

        for col in cols_to_check:
            if col not in self.df.columns:
                self._errors.append(
                    CheckError(row=1, column=col,
                               message="Столбец отсутствует — проверка невозможна")
                )
                continue

            empty_count = int(self._is_empty(self.df[col]).sum())
            empty_percent = empty_count / total_rows * 100
            is_invalid = (
                empty_count == total_rows
                if max_empty_percent is None
                else empty_percent > max_empty_percent
            )
            if is_invalid:
                col_errors = sum(1 for error in self._errors if error.column == col)
                if col_errors >= max_errors_per_column:
                    continue
                message = (
                    "колонка полностью пуста: 0% заполненности"
                    if max_empty_percent is None
                    else (
                        f"{empty_percent:.1f}% пустых значений "
                        f"(порог {max_empty_percent}%) — "
                        f"пусто {empty_count} из {total_rows} строк"
                    )
                )
                self._errors.append(
                    CheckError(
                        row=1,
                        column=col,
                        message=message,
                    )
                )
        return self

    def check_no_duplicate_rows(
        self,
        columns: Optional[Sequence[str]] = None,
        message: str = "полный дубликат строки",
    ) -> ExcelDataQualityChecker:
        """Проверяет, что нет полностью совпадающих строк по указанным столбцам.
    
        Что проверяет:
            Для каждой группы строк, где значения во всех указанных столбцах
            совпадают, фиксирует ошибку. Пустые значения (NaN, '') участвуют
            в сравнении — строки с одинаковыми пустыми ячейками считаются дубликатами.
    
        Параметры:
            columns: Список имён столбцов, по которым проверяется уникальность.
                Если не указан, проверяется полное совпадение строк.
            message: Текст ошибки (по умолчанию "полный дубликат строки").
    
        Пример в тесте:
            >>> checker.check_no_duplicate_rows(["Должность", "ФИО", "Дата списания"])
            >>> checker.check_no_duplicate_rows(
            ...     ["Заказ/название", "Затраченное время в минутах"],
            ...     message="дублирующая запись по заказу и времени",
            ... )
        """
        columns_to_check = list(columns) if columns is not None else list(self.df.columns)
        missing = [c for c in columns_to_check if c not in self.df.columns]
        if missing:
            self._errors.append(
                CheckError(row=1, column="STRUCTURE",
                           message=f"Отсутствуют столбцы для проверки дубликатов: {missing}")
            )
            return self
    
        # Находим дубликаты: keep=False помечает все строки группы-дубликата
        dup_mask = self.df.duplicated(subset=columns_to_check, keep=False)
        dup_indices = self.df[dup_mask].index.tolist()
    
        # Помечаем все строки группы как ошибочные
        # Если нужно оставить первую строку без ошибки — замените на:
        # dup_extra_mask = self.df.duplicated(subset=list(columns), keep='first')
        # dup_indices = self.df[dup_extra_mask].index.tolist()
        for idx in dup_indices:
            self._errors.append(
                CheckError(
                    row=idx + 2,
                    column=", ".join(columns_to_check),
                    message=message,
                )
            )
    
        return self
    
    def check_filename(
        self,
        expected_name: Optional[str] = None,
        expected_pattern: Optional[str] = None,
        expected_suffix: Optional[str] = None,
        actual_name: Optional[str] = None,
        case_sensitive: bool = True,
        message: str = "некорректное имя файла",
    ) -> ExcelDataQualityChecker:
        r"""Проверяет имя файла.

        Что проверяет:
            - При заданном ``expected_name`` — точное совпадение.
            - При заданном ``expected_pattern`` — соответствие регулярному выражению.
            - При заданном ``expected_suffix`` — окончание имени файла.

            По умолчанию проверяется имя файла, переданное при создании
            ``ExcelDataQualityChecker``. Если нужно проверить другое имя
            (например, оригинальное имя из заголовка API), передайте его
            в ``actual_name``.

        Параметры:
            expected_name: Ожидаемое точное имя файла.
            expected_pattern: Регулярное выражение для проверки.
            expected_suffix: Ожидаемое окончание имени файла.
            actual_name: Имя файла для проверки. По умолчанию — ``self.path.name``.
            case_sensitive: Учитывать ли регистр.
            message: Текст ошибки.

        Пример в тесте:
            >>> # Проверка имени скачанного файла
            >>> checker.check_filename(expected_suffix=".xlsx")
            >>> # Проверка оригинального имени из API
            >>> checker.check_filename(
            ...     actual_name=calc.original_filename,
            ...     expected_pattern=r"^[0-9a-f]{32}_timesheet_report_.*\.xlsx$",
            ... )
        """
        name = actual_name if actual_name is not None else self.path.name

        if name is None:
            self._errors.append(
                CheckError(
                    row=1, column="FILENAME",
                    message=f"{message}: имя файла не задано",
                )
            )
            return self

        if expected_name is not None:
            if case_sensitive:
                match = name == expected_name
            else:
                match = name.lower() == expected_name.lower()
            if not match:
                self._errors.append(
                    CheckError(
                        row=1, column="FILENAME",
                        message=f"{message}: ожидалось '{expected_name}', получено '{name}'",
                    )
                )
            return self

        if expected_pattern is not None:
            flags = 0 if case_sensitive else re.IGNORECASE
            if not re.search(expected_pattern, name, flags=flags):
                self._errors.append(
                    CheckError(
                        row=1, column="FILENAME",
                        message=f"{message}: '{name}' не соответствует шаблону '{expected_pattern}'",
                    )
                )
            return self

        if expected_suffix is not None:
            if case_sensitive:
                match = name.endswith(expected_suffix)
            else:
                match = name.lower().endswith(expected_suffix.lower())
            if not match:
                self._errors.append(
                    CheckError(
                        row=1, column="FILENAME",
                        message=f"{message}: ожидалось окончание '{expected_suffix}', получено '{name}'",
                    )
                )
            return self

        return self









    def assert_valid(self, max_examples: int = 3) -> None:
        """Завершает проверку и выводит все накопленные ошибки.

        Параметры:
            max_examples: Сколько строк с фактическими значениями показать
                для каждого нарушенного правила. По умолчанию ``3``.

        Если ошибок нет, метод ничего не делает. Если есть, тест завершается
        с ``AssertionError``: правило, количество ошибок, номера строк и
        примеры значений выводятся одним понятным сообщением.
        """
        if not self._errors:
            return

        from collections import defaultdict

        groups = defaultdict(list)
        for e in self._errors:
            groups[(e.column, e.message)].append(e)

        blocks = []
        blocks.append(f"Отчёт: {self.path.name}")

        for (col, msg), errors in sorted(groups.items(), key=lambda x: x[0][0]):
            count = len(errors)
            rows = sorted({e.row for e in errors})
            shown = rows[:max_examples]
            rows_str = ", ".join(str(r) for r in shown)
            if count > len(shown):
                rows_str += f" ... и ещё {count - len(shown)}"

            # Для FILENAME — показываем сам message (там уже есть описание проблемы)
            if col == "FILENAME":
                comment = f"{count} ошибок: {msg}"
            elif "дубликат" in msg.lower() or "совпадение" in msg.lower():
                comment = f"Правило: {msg}. Дубликатов: {count}. Строки: {rows_str}"
            else:
                comment = f"Правило: {msg}. Ошибок: {count}. Строки: {rows_str}"

            block = (
                f'"{col}" → '
                f'{comment}'
            )
            examples = [
                f"строка {error.row}: {self._format_error_value(error.value)}"
                for error in errors[:max_examples]
                if error.value is not None
            ]
            if examples:
                block += f"\nПримеры значений: {'; '.join(examples)}"
            blocks.append(block)

        raise AssertionError("\n\n" + "\n\n".join(blocks))
