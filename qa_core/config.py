"""Чтение секций корневого ``config.yaml`` для компонентов ядра и плагинов.

Зачем нужен файл:
    Файл знает только, как найти YAML и достать из него одну секцию. Модель
    секции описывает сам компонент рядом со своим кодом, поэтому новый плагин
    добавляет собственную секцию, не изменяя ядро.

Правила:
    - ``config.yaml`` необязателен: если файла или секции нет, используются
      значения по умолчанию из модели;
    - неизвестные секции игнорируются, они принадлежат другим компонентам;
    - неизвестный ключ внутри секции — ошибка, чтобы опечатки не терялись.

Как использовать в своём компоненте:

    >>> class KafkaSettings(BaseModel):
    ...     model_config = ConfigDict(extra="forbid", frozen=True)
    ...     bootstrap: str = "localhost:9092"
    >>> kafka = load_section("kafka", KafkaSettings)
    >>> test_kafka = load_section("kafka", KafkaSettings, "configs/test.yaml")
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel, ValidationError

DEFAULT_CONFIG_NAME = "config.yaml"

ModelT = TypeVar("ModelT", bound=BaseModel)


def load_section(
    name: str,
    model: type[ModelT],
    config_path: str | Path | None = None,
) -> ModelT:
    """Возвращает проверенную секцию ``name`` из указанного или корневого YAML."""
    path = Path(config_path) if config_path is not None else Path.cwd() / DEFAULT_CONFIG_NAME
    raw_section = _read_yaml(path.resolve()).get(name)
    if raw_section is None:
        raw_section = {}
    if not isinstance(raw_section, dict):
        raise ValueError(f"Секция '{name}' в {path} должна быть словарём ключей и значений")

    try:
        return model.model_validate(raw_section)
    except ValidationError as exc:
        raise ValueError(f"Некорректная секция '{name}' в {path}:\n{exc}") from None


@lru_cache
def _read_yaml(path: Path) -> dict[str, Any]:
    """Читает каждый файл один раз; отсутствующий файл равен пустой конфигурации."""
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as config_file:
        content = yaml.safe_load(config_file) or {}
    if not isinstance(content, dict):
        raise ValueError(f"Корень {path} должен быть словарём секций")
    return content
