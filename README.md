# qa-core

Переиспользуемое ядро тестовой инфраструктуры. Репозиторий устроен как обычная
Python-библиотека: реализация находится в `qa_core`, её тесты — в `tests`, а
короткие примеры публичных методов — в `Шпаргалка.md`.

## Структура

```text
qa_core/
├── checks/             # проверки Excel и OData
├── clients/            # HTTP- и PostgreSQL-клиенты
├── sources/            # подготовка данных для checker-ов
├── pytest_plugins/     # переиспользуемые плагины pytest
└── config.py           # единая загрузка config.yaml
tests/                  # тесты самого qa-core
config.yaml             # настройки компонентов
Шпаргалка.md             # примеры использования
pyproject.toml          # установка, зависимости и настройки pytest
```

Папка `база для разбора` — временный архив исходного проекта. Она не входит в
пакет и не участвует в запуске тестов.

## Первый запуск

Требуется Python 3.11 или новее. В PowerShell из корня репозитория:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
```

Настройки pytest находятся в `pyproject.toml`, поэтому обычная команда
`python -m pytest` запускает только корневую папку `tests` и не заходит в архив.

## Что относится к ядру

Ядро разделено на простые слои:

1. `clients` подключаются к HTTP, PostgreSQL и другим транспортам;
2. `sources` приводят полученные данные к входу, понятному checker-у;
3. `checks` проверяют данные и не знают, откуда они пришли;
4. проектные `tests` собирают эти части как кубики.

- `BaseHttpClient` — отправка HTTP-запросов и диагностическое логирование;
- `PostgresClient` — выполнение параметризованных запросов к PostgreSQL;
- `ExcelSource` — подготовка Excel из файла, байтов или HTTP-ответа с сохранением исходного имени;
- `ExcelDataQualityChecker` — последовательные проверки Excel-отчётов;
- `OdataAssertions` — проверки структуры и поведения OData-ответов;
- `allure_reporting` — вложение логов упавшего теста в Allure;
- `playwright` — browser lifecycle, скриншот и trace при падении UI-теста;
- `load_settings` — единая загрузка и проверка корневого YAML.

Клиенты конкретных систем, URL, токены, payload, Page Objects и бизнес-тесты
остаются в репозитории подключающего проекта.

## Использование в другом проекте

Установите пакет из внутреннего registry или Git, затем импортируйте нужный
компонент:

```python
from qa_core.clients.http import BaseHttpClient
from qa_core.checks.excel import ExcelDataQualityChecker
```

Для Allure-плагина установите extra `allure` и подключите его в проектном
`conftest.py`:

```python
pytest_plugins = ["qa_core.pytest_plugins.allure_reporting"]
```

Для UI-тестов установите extra `ui` и подключите оба плагина:

```python
pytest_plugins = [
    "qa_core.pytest_plugins.allure_reporting",
    "qa_core.pytest_plugins.playwright",
]
```

Практические примеры находятся в [Шпаргалка.md](Шпаргалка.md).
