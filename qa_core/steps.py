"""Шаг теста: строка в логе и, если установлен allure, шаг в отчёте.

Один вызов вместо ``allure.step`` и перехвата его в логи. Без allure работает так же:
пишет в лог ``STEP: ...``, поэтому код ядра и Page Object не требуют Allure.

    with step("Открыть страницу заказов"):
        ...
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@contextmanager
def step(name: str) -> Iterator[None]:
    logger.info("STEP: %s", name)
    try:
        import allure
    except ImportError:
        yield
        return
    with allure.step(name):
        yield
