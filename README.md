# qa-core (репозиторий qa-harness)

Набор готовых кирпичиков для автотестов: HTTP-клиент, PostgreSQL, проверки Excel и OData,
плагины pytest для логов, Allure и браузера Playwright.

Ставите только то, что нужно проекту, подключаете одной строкой и сразу пишете тесты. URL,
токены, payload, локаторы и бизнес-правила остаются в вашем проекте.

Команды даны для Windows и PowerShell.

**Содержание:**
[Быстрый старт](#быстрый-старт) ·
[Наборы компонентов](#наборы-компонентов) ·
[Настройка](#настройка) ·
[Секреты](#секреты) ·
[Свой плагин](#свой-плагин) ·
[Если что-то не работает](#если-что-то-не-работает) ·
[Словарик](#словарик) ·
[Устройство](#устройство-репозитория)

Другие документы: [Шпаргалка.md](Шпаргалка.md) (короткие примеры на каждый компонент),
[Правила.md](Правила.md) (как оформлять тесты), [examples](examples/README.md) (запускаемые примеры).

## Быстрый старт

Нужны Python 3.11 или новее (проверка: `python --version`) и доступ к репозиторию на GitHub.

**1. Создайте папку проекта и виртуальное окружение.** Виртуальное окружение — это папка `.venv`, в
которую ставятся библиотеки проекта, чтобы они не мешали другим проектам.

```powershell
mkdir мой-проект
cd мой-проект
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

В начале строки появится `(.venv)`. Активировать окружение нужно в каждом новом окне PowerShell.

<<<<<<< HEAD
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
=======
> Если PowerShell пишет, что выполнение скриптов запрещено, один раз выполните
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` и повторите активацию.

**2. Установите qa-core** с нужными компонентами (список — в [таблице ниже](#наборы-компонентов)):

```powershell
python -m pip install "qa-core[http,excel,allure] @ git+https://github.com/Pauelbel/qa-harness.git"
```

Для тестов в браузере добавьте набор `ui` и один раз скачайте браузер:
>>>>>>> 4bb577fd1ea6e130ec43756d6213dcc872789e4f

```powershell
python -m pip install "qa-core[ui] @ git+https://github.com/Pauelbel/qa-harness.git"
python -m playwright install chromium
```

**3. Подключите плагины.** Создайте в папке проекта файл `conftest.py`:

```python
pytest_plugins = [
    "qa_core.pytest_plugins.logging",           # логи в консоль и в папку logs/
    "qa_core.pytest_plugins.allure_reporting",  # логи упавшего теста в Allure
]
```

<<<<<<< HEAD
Настройки pytest находятся в `pyproject.toml`. Для запуска проверок самого ядра установите
наборы `backend,allure,test` и запустите:
=======
**4. Напишите тест.** Создайте файл `test_first.py`:

```python
from qa_core.clients.http import BaseHttpClient

def test_service_is_available():
    with BaseHttpClient() as http:
        response = http.get("https://example.com")
    assert response.status_code == 200
```

**5. Запустите:**
>>>>>>> 4bb577fd1ea6e130ec43756d6213dcc872789e4f

```powershell
python -m pytest
```

<<<<<<< HEAD
Только HTTP-проверки требуют набора `test` и запускаются без Allure:

```powershell
python -m pip install -e ".[test]"
python -m pytest tests/test_http.py
```

Проверка явной загрузки YAML пропускается, если не установлен набор `config`.

## Что относится к ядру
=======
В консоли идут логи: адрес запроса, код ответа, время. Значения `token`, `password` и похожих
параметров в адресе заменены на `***`. Весь подробный лог сохраняется в папку `logs\`. Для поиска
причины ошибки: `python -m pytest --log-cli-level=DEBUG`.
>>>>>>> 4bb577fd1ea6e130ec43756d6213dcc872789e4f

Файл `config.yaml` для старта не нужен: без него работают значения по умолчанию.

### Быстрее: заготовка проекта

<<<<<<< HEAD
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
=======
Когда `qa-core` уже установлен, команда `qa-core init` создаёт за вас `conftest.py`, `pytest.ini`,
`requirements.txt`, `.gitignore`, `config.yaml` (если нужен) и по рабочему тесту на каждый компонент:
>>>>>>> 4bb577fd1ea6e130ec43756d6213dcc872789e4f

```powershell
qa-core init --components http,excel,allure
```

<<<<<<< HEAD
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
=======
Если команда `qa-core` не найдена, используйте `python -m qa_core init --components http,excel,allure`.
Существующие файлы она не перезаписывает. Компоненты: `http`, `db`, `excel`, `odata`, `allure`, `ui`.
>>>>>>> 4bb577fd1ea6e130ec43756d6213dcc872789e4f

### Allure-отчёт

<<<<<<< HEAD
Для `allure_reporting` сначала установите набор `allure`.

```python
pytest_plugins = [
    "qa_core.pytest_plugins.logging",           # консольные и файловые логи
    "qa_core.pytest_plugins.allure_reporting",  # логи и Allure-отчёт
    "qa_core.pytest_plugins.playwright",         # frontend-фикстура browser_page
]
=======
```powershell
python -m pytest --alluredir=allure-results
allure generate --single-file -c ./allure-results
>>>>>>> 4bb577fd1ea6e130ec43756d6213dcc872789e4f
```

Получится один HTML-файл `allure-report\index.html`, его можно открыть в браузере. Программа `allure`
ставится отдельно (Allure Commandline), не через pip.

## Наборы компонентов

В базовую установку входит только чтение `config.yaml` и pytest. Остальное выбирается наборами, их
можно перечислять через запятую: `qa-core[http,excel]`.

| Набор | Что даёт | Импорт |
| --- | --- | --- |
| `http` | HTTP-клиент с логами и маскированием токенов | `qa_core.clients.http.BaseHttpClient` |
| `db` | Запросы в PostgreSQL | `qa_core.clients.postgres.PostgresClient` |
| `excel` | Проверка качества Excel-отчётов | `qa_core.checks.excel.ExcelDataQualityChecker`, `qa_core.sources.excel.ExcelSource` |
| `odata` | Проверки ответов OData | `qa_core.checks.odata.OdataAssertions` |
| `allure` | Логи упавшего теста в Allure, окружение запуска | плагин `allure_reporting` |
| `ui` | Браузер Playwright со скриншотом и trace при падении | плагин `playwright` |
| `vault` | Чтение секретов из HashiCorp Vault | `qa_core.secrets.SecretStore` |

Готовые сочетания: `backend` (`http`, `db`, `excel`, `odata`, `allure`), `frontend` (`ui`) и `all` (всё сразу).

### Плагины pytest

Плагины подключаются списком в `conftest.py`. Каждый работает сам по себе, без остальных:

| Плагин | Что делает | Нужен набор |
| --- | --- | --- |
| `qa_core.pytest_plugins.logging` | Логи в консоль и в файл `logs/pytest_<окружение>.log` | — |
| `qa_core.pytest_plugins.allure_reporting` | Прикладывает логи к упавшему тесту, пишет `environment.xml` | `allure` |
| `qa_core.pytest_plugins.playwright` | Фикстура `browser_page`: один браузер на запуск, чистая страница на тест (вход можно сделать один раз через `qa_storage_state`); скриншот и trace при падении | `ui` |

Имя окружения для логов и Allure берётся из `--qa-environment=dev` или из переменной `TEST_ENV`.

## Настройка

Файл `config.yaml` необязателен и лежит в папке, откуда запускается pytest. Каждый компонент читает
только свою секцию, остальные игнорирует.

```yaml
http:
  timeout: 30                             # секунд на ответ, если в вызове не указан свой
  max_logged_response_body_length: 2000   # сколько символов ответа писать в лог
  sensitive_query_parameters: [token, api_key, password]   # значения станут ***

browser:
  engine: chromium        # chromium, firefox или webkit
  headless: true          # false — показывать окно браузера
  width: 1920
  height: 1080
  ignore_https_errors: true
```

Если секции нет, действуют значения по умолчанию. Если нет самого файла, в логе один раз появится
предупреждение с путём (так заметен запуск не из той папки). Опечатка в названии ключа внутри секции
даёт понятную ошибку с именем секции. Опечатка в названии самой секции (`htpp:`) не замечается.

<<<<<<< HEAD
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
=======
## Секреты

`SecretStore` читает пароли и токены из переменных окружения или из Vault. Он никогда не переходит на
другой источник сам: если ключа нет, вы получите ошибку с его именем.

| Переменная | Значение |
| --- | --- |
| `SECRETS_SOURCE` | `env` (по умолчанию) или `vault` |
| `VAULT_ADDR`, `VAULT_MOUNT`, `VAULT_PATH` | где лежит секрет в Vault |
| `VAULT_KV_VERSION` | `1` или `2` (по умолчанию `2`) |
| `VAULT_TOKEN` | либо пара `VAULT_ROLE_ID` и `VAULT_SECRET_ID` |
| `VAULT_CACERT` | путь к своему CA; `VAULT_VERIFY=false` отключает проверку TLS |

Для Vault нужен набор `vault`. Пример использования — в [Шпаргалке](Шпаргалка.md#секреты).

## Свой плагин

Отдельной системы плагинов нет: используется pytest. Есть два способа.

**Плагин внутри проекта.** Обычный модуль с фикстурами и хуками. Подключите его в `pytest_plugins` в
`conftest.py` рядом с плагинами qa-core.

**Плагин отдельным пакетом** (например, `qa-core-jira`). В его `pyproject.toml` укажите зависимость на
`qa-core` и точку входа:

```toml
[project.entry-points.pytest11]
qa_core_jira = "qa_core_jira.plugin"
```

После `pip install` такой плагин подключается сам.

Собственную секцию в `config.yaml` плагин описывает моделью рядом со своим кодом и читает так:

```python
from pydantic import BaseModel, ConfigDict
from qa_core.config import load_section


class JiraSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    url: str = "https://jira.example"


settings = load_section("jira", JiraSettings)
```

Ядро менять не нужно. Полный пример — в [Шпаргалке](Шпаргалка.md#свой-плагин).

## Если что-то не работает

| Что видите | Что делать |
| --- | --- |
| `No module named 'pandas'` (или `requests`, `allure`, `playwright`) | не поставлен нужный набор: установите его, например `qa-core[excel]` |
| `Файл конфигурации не найден` | запуск не из той папки. Запускайте `python -m pytest` из папки, где лежит `config.yaml`. Если файл не нужен, предупреждение можно игнорировать |
| `command not found: qa-core` или `qa-core не распознано` | используйте `python -m qa_core init ...` или проверьте, что окружение активировано |
| `выполнение скриптов отключено` при активации окружения | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Тест долго «висит» | запрос ждёт ответ: по умолчанию 30 секунд, потом тест упадёт с ошибкой |
| Браузер не запускается | `python -m playwright install chromium` |
| `Для Vault установите дополнительную зависимость` | установите набор `vault` |
| Ошибка доступа при `pip install ... git+https://...` | нет доступа к репозиторию с этого компьютера: проверьте доступ в Git |

## Словарик

| Слово | Что значит |
| --- | --- |
| Тест | функция, имя которой начинается с `test_`. Она падает, если проверка не прошла |
| `assert` | проверка: `assert response.status_code == 200` — «код ответа должен быть 200» |
| Фикстура | подготовка для теста. Тест пишет её имя в аргументах и получает готовое значение |
| Плагин | готовая возможность, подключаемая в `conftest.py`: логи, отчёты, браузер |
| Allure | инструмент красивых отчётов о запуске |
| Окружение (стенд) | среда, на которой идёт запуск: dev, stage, prod |
| Виртуальное окружение | папка `.venv` с библиотеками проекта, чтобы они не мешали другим проектам |
| Секрет | пароль или токен: в коде тестов их не пишут, а читают из переменных окружения или Vault |

## Устройство репозитория

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
tests/                 # тесты самого qa-core
examples/              # запускаемые примеры использования
config.yaml            # пример настроек
Шпаргалка.md           # примеры кода
Правила.md             # правила оформления тестов
```

Что остаётся в вашем проекте: URL и авторизация, payload, SQL, локаторы, модели ответов и сами
бизнес-тесты.

### Разработка самого qa-core

Для тех, кто меняет код библиотеки: скачайте репозиторий, создайте окружение, поставьте пакет из папки
(правки действуют сразу) и запустите тесты и примеры:

```powershell
git clone https://github.com/Pauelbel/qa-harness.git
cd qa-harness
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[all]"
python -m pytest
```
>>>>>>> 4bb577fd1ea6e130ec43756d6213dcc872789e4f
