"""Чтение настроек из файла ``config.py`` в корне проекта.

Зачем нужен файл:
    Настройки лежат в обычном Python-файле ``config.py`` рядом с тестами: одна
    секция — один словарь с именем в верхнем регистре (``HTTP``, ``BROWSER``).
    Модель секции описывает сам компонент рядом со своим кодом, поэтому новый
    плагин добавляет собственную секцию, не изменяя ядро.

Правила:
    - ``config.py`` необязателен: если файла или секции нет, используются
      значения по умолчанию из модели, а об отсутствующем файле один раз
      пишется предупреждение в лог;
    - неизвестные секции игнорируются, они принадлежат другим компонентам;
    - неизвестный ключ внутри секции — ошибка, чтобы опечатки не терялись.

Пример ``config.py`` проекта:

    HTTP = {"timeout": 30}
    BROWSER = {"headless": False}
    KAFKA = {"bootstrap": "kafka:9092"}

Как использовать в своём компоненте:

    >>> class KafkaSettings(BaseModel):
    ...     model_config = ConfigDict(extra="forbid", frozen=True)
    ...     bootstrap: str = "localhost:9092"
    >>> kafka = load_section("kafka", KafkaSettings)   # читает KAFKA из config.py

Файл ``config.py`` должен быть виден для импорта: pytest запускают из корня
проекта (``pythonpath = .`` в настройках pytest).
"""

from __future__ import annotations

import importlib
import logging
from functools import lru_cache
from types import ModuleType
from typing import TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

PROJECT_CONFIG_MODULE = "config"

ModelT = TypeVar("ModelT", bound=BaseModel)


def load_section(name: str, model: type[ModelT]) -> ModelT:
    """Возвращает проверенную секцию ``name`` из ``config.py`` проекта."""
    module = _project_config()
    raw_section = getattr(module, name.upper(), None) if module is not None else None
    if raw_section is None:
        raw_section = {}
    if not isinstance(raw_section, dict):
        raise ValueError(
            f"{name.upper()} в {PROJECT_CONFIG_MODULE}.py должна быть словарём ключей и значений"
        )

    try:
        return model.model_validate(raw_section)
    except ValidationError as exc:
        raise ValueError(
            f"Некорректная секция {name.upper()} в {PROJECT_CONFIG_MODULE}.py:\n{exc}"
        ) from None


@lru_cache
def _project_config() -> ModuleType | None:
    """Импортирует ``config.py`` один раз; отсутствующий файл равен пустым настройкам."""
    try:
        return importlib.import_module(PROJECT_CONFIG_MODULE)
    except ModuleNotFoundError as exc:
        if exc.name != PROJECT_CONFIG_MODULE:
            raise  # ошибка внутри самого config.py не должна скрываться
        # Предупреждение выходит один раз благодаря кэшу: так запуск не из той
        # папки не остаётся незамеченным.
        logger.warning(
            "Файл %s.py не найден. Используются значения по умолчанию.",
            PROJECT_CONFIG_MODULE,
        )
        return None
