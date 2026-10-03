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
├── config.py           # единая загрузка config.yaml
└── secrets.py          # чтение секретов из env или Vault
tests/                  # тесты самого qa-core
config.yaml             # настройки компонентов
Шпаргалка.md             # примеры использования
pyproject.toml          # установка, зависимости и настройки pytest
```

## Первый запуск

Требуется Python 3.11 или новее. В PowerShell из корня репозитория:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### Установка зависимостей

Выберите нужные наборы зависимостей. Каждый набор можно установить отдельно
или объединить с другими через запятую. Базовая установка содержит только
HTTP-транспорт (`requests`). Allure подключается отдельным набором `allure`;
`frontend` работает без него и сохраняет браузерную диагностику локально.

```powershell
# Минимальное ядро: HTTP без YAML, pytest и Allure
python -m pip install -e .

# Необязательная загрузка настроек из YAML
python -m pip install -e ".[config]"

# Allure и его pytest-плагин
python -m pip install -e ".[allure]"

# Backend-тесты: HTTP, PostgreSQL, Excel и OData
python -m pip install -e ".[backend]"

# Frontend-тесты: Python-библиотека Playwright
python -m pip install -e ".[frontend]"

# Подключение к Vault: Python-библиотека hvac
python -m pip install -e ".[vault]"
```

Можно установить несколько наборов одной командой:

```powershell
# Backend и frontend вместе
python -m pip install -e ".[backend,frontend]"

# Все расширения и зависимости тестов самого пакета
python -m pip install -e ".[backend,frontend,vault,allure,test]"
```

#### Дополнительные настройки frontend

Если выбран `frontend`, после установки пакета отдельно установите браузер Chromium:

```powershell
python -m playwright install chromium
```

#### Дополнительные настройки Vault

Набор `vault` устанавливает библиотеку `hvac` для подключения, а не сервер Vault.
Для чтения секретов задайте `SECRETS_SOURCE=vault`, адрес `VAULT_ADDR`, точку
монтирования `VAULT_MOUNT` и путь `VAULT_PATH`. Для авторизации укажите
`VAULT_TOKEN` либо пару `VAULT_ROLE_ID` и `VAULT_SECRET_ID`.
Версия KV задаётся через `VAULT_KV_VERSION` (`1` или `2`, по умолчанию `2`).
Если секреты читаются только из переменных окружения или `.env`, набор `vault`
не нужен.

Настройки pytest находятся в `pyproject.toml`. Для запуска проверок самого ядра установите
наборы `backend,allure,test` и запустите:

```powershell
python -m pytest
```

Только HTTP-проверки требуют набора `test` и запускаются без Allure:

```powershell
python -m pip install -e ".[test]"
python -m pytest tests/test_http.py
```

Проверка явной загрузки YAML пропускается, если не установлен набор `config`.

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
- `logging` — единый формат консольных и файловых логов pytest;
- `allure_reporting` — вложение логов упавшего теста в Allure;
- `diagnostics` — контракт файлов и общие события диагностических расширений;
- `playwright` — browser lifecycle, скриншот и trace при падении frontend-теста;
- `load_settings` — единая загрузка и проверка корневого YAML.
- `SecretStore` — чтение обязательных значений из `env` или Vault, независимо от pytest.

Клиенты конкретных систем, URL, токены, payload, Page Objects и бизнес-тесты
остаются в репозитории подключающего проекта.

## Использование в другом проекте

Установите пакет из внутреннего registry или Git, затем импортируйте нужный
компонент:

```python
from qa_core.clients.http import BaseHttpClient
from qa_core.checks.excel import ExcelDataQualityChecker
```

### HTTP без расширений

Клиент получает настройки через код и по умолчанию не читает `config.yaml`:

```python
from qa_core.clients.http import BaseHttpClient

with BaseHttpClient(
    sensitive_query_parameters=["token", "api_key"],
    max_logged_response_body_length=1000,
) as http:
    response = http.get("https://service.example/api/items", timeout=10)
    response.raise_for_status()
```

По умолчанию маскируются `token`, `access_token`, `api_key`, `key`, `password`,
а тело ответа в логе ограничено 2000 символами. Для явной загрузки YAML
установите набор `config` и передайте `config_path="configs/test.yaml"`.
Параметры конструктора имеют приоритет над значениями из YAML.

### Подключение pytest-плагинов

Добавьте нужные плагины в корневой `conftest.py` вашего проекта:

Для `allure_reporting` сначала установите набор `allure`.

```python
pytest_plugins = [
    "qa_core.pytest_plugins.logging",           # консольные и файловые логи
    "qa_core.pytest_plugins.allure_reporting",  # логи и Allure-отчёт
    "qa_core.pytest_plugins.playwright",         # frontend-фикстура browser_page
]
```

Если frontend-тестов нет, удалите из списка строку с `playwright`.

После этого в frontend-тестах доступна готовая фикстура `browser_page`:

```python
import allure


@allure.epic("Frontend")
@allure.title("Проверка главной страницы")
def test_home_page(browser_page):
    with allure.step("Открыть главную страницу"):
        browser_page.goto("https://example.com")

    with allure.step("Проверить заголовок"):
        assert browser_page.title()
```

`logging` настраивает вывод и пишет файл в папку `logs` подключившего проекта,
`allure_reporting` прикладывает логи к упавшему тесту, а `playwright` создаёт
браузерную страницу и сохраняет скриншот и trace при падении.

### Браузерная диагностика без Allure

Установите набор `frontend` и подключите только браузерный плагин:

```python
pytest_plugins = ["qa_core.pytest_plugins.playwright"]
```

При падении теста или зависимой фикстуры скриншот и trace сохраняются в
`test-artifacts/<имя-теста>-<идентификатор>/`. Для каждого теста создаётся свой
каталог; при успешном тесте диагностические файлы не создаются. Корневой
каталог можно изменить через `--qa-artifacts-dir=diagnostics`; относительный
путь отсчитывается от корня pytest-проекта. Закрытая страница или ошибка
скриншота не мешает сохранению trace.

Для вложений в Allure установите `.[frontend,allure]`, добавьте
`qa_core.pytest_plugins.allure_reporting` в `pytest_plugins` и запустите pytest
с `--alluredir=allure-results`. Локальные файлы сохраняются в обоих режимах.
Порядок подключения браузерного плагина и отчётчика не имеет значения.

### Контракт диагностических расширений

`DiagnosticArtifact` из `qa_core.diagnostics` описывает готовый файл: путь,
название, MIME-тип и расширение. Контракт использует только стандартную
библиотеку Python. Общий pytest-плагин `qa_core.pytest_plugins.diagnostics`
объявляет событие `pytest_qa_attach_artifact(item, artifact)` и сохраняет
результаты стадий теста. Playwright и Allure подключают его автоматически.

Источник сначала сохраняет файл, затем публикует событие:

```python
from qa_core.diagnostics import DiagnosticArtifact

request.config.hook.pytest_qa_attach_artifact(
    item=request.node,
    artifact=DiagnosticArtifact(path, "Диагностика", "application/zip", "zip"),
)
```

Другой отчётчик может подписаться на то же событие в своём pytest-плагине:

```python
pytest_plugins = ["qa_core.pytest_plugins.diagnostics"]

def pytest_qa_attach_artifact(item, artifact):
    # Здесь отчётчик прикладывает artifact.path к своему отчёту.
    ...
```

Событие вызывается у всех подключённых обработчиков. При отсутствии
отчётчиков файлы остаются в локальном каталоге.

Практические примеры находятся в [Шпаргалка.md](Шпаргалка.md).
