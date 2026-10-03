"""Общие части плагинов, чтобы каждый плагин работал без остальных.

Зачем нужен файл:
    Опция ``--qa-environment`` и сохранение результата стадий теста нужны
    нескольким плагинам. Каждый плагин импортирует их отсюда, поэтому не
    зависит от того, подключены ли соседние плагины.

Повторная регистрация безопасна: опция добавляется один раз, а запись
результата стадии выполняется одинаково в любом количестве плагинов.
"""

from __future__ import annotations

import pytest


def add_environment_option(parser) -> None:
    """Добавляет ``--qa-environment``, если другой плагин ещё не сделал этого."""
    group = parser.getgroup("qa-core")
    try:
        group.addoption(
            "--qa-environment",
            action="store",
            default=None,
            help="Имя окружения для логов и environment.xml в Allure-результатах",
        )
    except ValueError:
        # Опцию уже зарегистрировал другой плагин qa-core.
        pass


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Сохраняет отчёт каждой стадии на объекте теста как ``report_<стадия>``."""
    del call
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"report_{report.when}", report)
