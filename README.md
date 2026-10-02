# qa-core

Набор готовых кирпичиков для автотестов: HTTP-клиент, PostgreSQL, проверки
Excel и OData, плагины pytest для логов, Allure и Playwright.

Ставите только то, что нужно проекту, подключаете одной строкой и сразу пишете
тесты. Всё остальное (URL, токены, payload, локаторы, бизнес-правила)
остаётся в вашем проекте.

**Новичку:** начните со страницы [Начало.md](Начало.md): за 15 минут вы запустите примеры и
свой первый тест. Правила оформления тестов — в [Правила.md](Правила.md).

Готовые примеры кода — в [Шпаргалке](Шпаргалка.md), а запускаемые тесты-примеры —
в папке [examples](examples/README.md). Они работают без внешних систем:

```powershell
python -m pytest examples
```

Примеры с браузером и PostgreSQL по умолчанию пропускаются: для браузера установите
Chromium и задайте `EXAMPLE_UI=1`, для базы — переменные из
[test_07_postgres_and_browser.py](examples/test_07_postgres_and_browser.py).

## Быстрый старт

Нужен Python 3.11 или новее.

Самый короткий путь — команда `qa-core init`: она создаст заготовку проекта (`conftest.py`,
`config.yaml`, `pytest.ini`, `requirements.txt` и по рабочему тесту на каждый компонент):

```powershell
qa-core init --components http,excel,allure
```

Ниже то же самое вручную.

**1. Установите нужные компоненты** (названия — в таблице ниже):

```powershell
python -m pip install "qa-core[http,excel,allure] @ git+https://github.com/Pauelbel/qa-harness.git"
```

**2. Подключите плагины** в `conftest.py` в корне проекта:

```python
pytest_plugins = [
    "qa_core.pytest_plugins.logging",
    "qa_core.pytest_plugins.allure_reporting",
]
```

**3. Пишите тест:**

```python
from qa_core.clients.http import BaseHttpClient

def test_items():
    with BaseHttpClient() as http:
        response = http.get("https://service.example/api/items", timeout=10)
    assert response.ok
```

Файл `config.yaml` для старта не нужен: без него работают значения по умолчанию.

## Что ставить

В базовую установку входит только чтение `config.yaml` и pytest. Остальное
выбирается наборами, их можно перечислять через запятую.

| Набор | Что даёт | Импорт |
| --- | --- | --- |
| `http` | HTTP-клиент с логами и маскированием токенов | `qa_core.clients.http.BaseHttpClient` |
| `db` | Запросы в PostgreSQL | `qa_core.clients.postgres.PostgresClient` |
| `excel` | Проверка качества Excel-отчётов | `qa_core.checks.excel.ExcelDataQualityChecker`, `qa_core.sources.excel.ExcelSource` |
| `odata` | Проверки ответов OData | `qa_core.checks.odata.OdataAssertions` |
| `allure` | Логи упавшего теста в Allure, окружение запуска | плагин `allure_reporting` |
| `ui` | Браузер Playwright со скриншотом и trace при падении | плагин `playwright` |
| `vault` | Чтение секретов из HashiCorp Vault | `qa_core.secrets.SecretStore` |

Готовые сочетания:

| Сочетание | Состав |
| --- | --- |
| `backend` | `http`, `db`, `excel`, `odata`, `allure` |
| `frontend` | `ui` |
| `all` | всё сразу |

Для набора `ui` после установки один раз скачайте браузер:

```powershell
python -m playwright install chromium
```

### Установка для разработки самого qa-core

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[all]"
python -m pytest
```

## Плагины pytest

Плагины подключаются списком в `conftest.py`. Каждый работает сам по себе, без
остальных.

| Плагин | Что делает | Нужен набор |
| --- | --- | --- |
| `qa_core.pytest_plugins.logging` | Логи в консоль и в файл `logs/pytest_<окружение>.log` | — |
| `qa_core.pytest_plugins.allure_reporting` | Прикладывает логи к упавшему тесту, пишет `environment.xml` | `allure` |
| `qa_core.pytest_plugins.playwright` | Фикстура `browser_page`: один браузер на запуск, чистая страница на тест (вход можно сделать один раз через `qa_storage_state`); скриншот и trace при падении | `ui` |

Имя окружения для логов и Allure берётся из `--qa-environment=dev` или из
переменной `TEST_ENV`.

## Настройка через config.yaml

Файл необязателен и лежит в папке, откуда запускается pytest. Каждый компонент
читает только свою секцию, остальные игнорирует.

```yaml
http:
  timeout: 30                             # секунд на ответ, если в вызове не указан свой
  max_logged_response_body_length: 2000   # сколько символов ответа писать в лог
  sensitive_query_parameters: [token, api_key, password]   # значения станут ***

browser:
  engine: chromium        # chromium, firefox или webkit
  headless: true
  width: 1920
  height: 1080
  ignore_https_errors: true
```

Если секции нет — действуют значения по умолчанию. Если нет самого файла, в логе
один раз появится предупреждение с путём (так заметен запуск не из той папки).
Опечатка в названии ключа внутри секции даёт понятную ошибку с именем секции.

## Секреты

`SecretStore` читает пароли и токены из переменных окружения или из Vault. Он
никогда не переходит на другой источник сам: если ключа нет, вы получите ошибку
с его именем.

| Переменная | Значение |
| --- | --- |
| `SECRETS_SOURCE` | `env` (по умолчанию) или `vault` |
| `VAULT_ADDR`, `VAULT_MOUNT`, `VAULT_PATH` | где лежит секрет в Vault |
| `VAULT_KV_VERSION` | `1` или `2` (по умолчанию `2`) |
| `VAULT_TOKEN` | либо пара `VAULT_ROLE_ID` и `VAULT_SECRET_ID` |
| `VAULT_CACERT` | путь к своему CA; `VAULT_VERIFY=false` отключает проверку TLS |

Пример использования — в [Шпаргалке](Шпаргалка.md#секреты).

## Свой плагин

Отдельной системы плагинов нет: используется pytest. Есть два способа.

**Плагин внутри проекта.** Обычный модуль с фикстурами и хуками. Подключите его
в `pytest_plugins` в `conftest.py` рядом с плагинами qa-core.

**Плагин отдельным пакетом** (например, `qa-core-jira`). В его `pyproject.toml`
укажите зависимость на `qa-core` и точку входа:

```toml
[project.entry-points.pytest11]
qa_core_jira = "qa_core_jira.plugin"
```

После `pip install` такой плагин подключается сам.

Собственную секцию в `config.yaml` плагин описывает моделью рядом со своим
кодом и читает так:

```python
from pydantic import BaseModel, ConfigDict
from qa_core.config import load_section


class JiraSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    url: str = "https://jira.example"


settings = load_section("jira", JiraSettings)
```

Ядро менять не нужно. Полный пример — в [Шпаргалке](Шпаргалка.md#свой-плагин).

## Как устроено ядро

Ядро состоит из четырёх слоёв, и каждый знает только о своём:

1. `clients` получают данные: HTTP, PostgreSQL.
2. `sources` приводят полученное к виду, понятному проверкам (например, сохраняют Excel).
3. `checks` проверяют данные и не знают, откуда они взялись.
4. Ваши тесты собирают эти части вместе.

```text
qa_core/
├── checks/            # проверки Excel и OData
├── clients/           # HTTP- и PostgreSQL-клиенты
├── sources/           # подготовка данных для проверок
├── pytest_plugins/    # плагины pytest: logging, allure_reporting, playwright
├── cli.py             # команда qa-core init
├── config.py          # чтение секций config.yaml
└── secrets.py         # чтение секретов из env или Vault
examples/              # запускаемые примеры использования
config.yaml            # пример настроек
Шпаргалка.md           # примеры кода
```

Что остаётся в вашем проекте: URL и авторизация, payload, SQL, локаторы,
модели ответов и сами бизнес-тесты.
