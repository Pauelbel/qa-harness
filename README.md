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

## Первый запуск

Требуется Python 3.11 или новее. В PowerShell из корня репозитория:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### Установка зависимостей

Базовая установка тянет только чтение `config.yaml` и pytest. Остальное ставится
наборами по компонентам, их можно перечислять через запятую:

| Набор | Что добавляет |
| --- | --- |
| `http` | `BaseHttpClient` (requests) |
| `db` | `PostgresClient` (psycopg2) |
| `excel` | `ExcelDataQualityChecker` и `ExcelSource` (pandas, openpyxl) |
| `odata` | `OdataAssertions` (pytest-check) |
| `allure` | плагин `allure_reporting` |
| `ui` | плагин `playwright` вместе с Allure |
| `vault` | чтение секретов из Vault (hvac) |

Готовые сочетания: `backend` (`http`, `db`, `excel`, `odata`, `allure`),
`frontend` (`ui`) и `all` (всё).

```powershell
# Только нужные компоненты
python -m pip install -e ".[http,excel,allure]"

# Всё сразу
python -m pip install -e ".[all]"
```

Из Git на другом проекте:

```powershell
python -m pip install "qa-core[http,excel,allure] @ git+https://github.com/Pauelbel/qa-harness.git"
```

#### Конфигурация

`config.yaml` необязателен: без файла или секции действуют значения по умолчанию.
Каждый компонент читает только свою секцию (`http`, `browser`), лишние секции
игнорируются, а неизвестный ключ внутри секции вызывает ошибку.

## Расширение плагинами

Своя система плагинов не нужна, используется pytest:

- **плагин проекта** — модуль, подключённый в `pytest_plugins` в `conftest.py`;
- **плагин отдельным пакетом** — пакет с зависимостью на `qa-core` и записью
  `[project.entry-points.pytest11]` в `pyproject.toml`, он подхватывается после `pip install`.

Собственную секцию конфига плагин описывает pydantic-моделью рядом со своим кодом
и читает через `qa_core.config.load_section("имя", Модель)`, не меняя ядро.

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
backend-зависимости и запустите:

```powershell
python -m pytest
```

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
- `playwright` — browser lifecycle, скриншот и trace при падении frontend-теста;
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

### Подключение pytest-плагинов

Добавьте нужные плагины в корневой `conftest.py` вашего проекта:

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

Практические примеры находятся в [Шпаргалка.md](Шпаргалка.md).
