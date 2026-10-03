# qa-harness

Переносимый QA-фреймворк на Python и pytest. Ядро (`qa_core/`) живёт отдельно от проекта:
правите здесь, на проектах подтягиваете. Правила тестов — в [Правила.md](Правила.md).

## Быстрый старт (новичку)

Нужны только [Docker](https://www.docker.com/products/docker-desktop/) и Git.

```bash
git clone https://github.com/Pauelbel/qa-harness.git
cd qa-harness
docker compose run --rm qa
```

Первая сборка занимает несколько минут. Логи и скриншоты упавших тестов появятся в `logs/`
и `test-artifacts/`. Части тестов запускаются по маркерам:

```bash
docker compose run --rm qa pytest -m smoke
docker compose run --rm qa pytest -m "not ui"
docker compose run --rm qa pytest examples/test_01_http.py
```

Без Docker: `pip install -e ".[http,ui,allure,dev]"`, затем `python -m playwright install chromium`
и `python -m pytest`.

## Ядро на своём проекте

В проект ставится пакет из git, только нужные наборы:

```bash
pip install "qa-core[http,ui] @ git+https://github.com/Pauelbel/qa-harness.git"
pip install --upgrade --force-reinstall --no-deps "qa-core @ git+https://github.com/Pauelbel/qa-harness.git"  # подтянуть новое ядро
```

| Набор | Что даёт |
| --- | --- |
| (без набора) | `config.py`, плагины `logging`, `fixtures` |
| `http` | `clients/http.py`: клиент с логами и маскировкой секретов |
| `db` | `clients/postgres.py` |
| `excel`, `odata` | проверки `checks/excel.py`, `checks/odata.py` |
| `allure` | плагин `allure_reporting` |
| `ui` | плагин `playwright`: фикстура `browser_page`, скриншот и trace при падении |
| `vault` | чтение секретов из Vault (`secrets.py`) |

Дальше скопируйте в проект [templates/](templates/), [Dockerfile](Dockerfile),
[docker-compose.yml](docker-compose.yml) и подключите плагины в `conftest.py`:

```python
pytest_plugins = [
    "qa_core.pytest_plugins.fixtures",   # маркеры api/ui/db/smoke/regression и http_client
    "qa_core.pytest_plugins.logging",    # логи в консоль и logs/
    "qa_core.pytest_plugins.playwright", # browser_page
]
```

**Отключить возможность:** не ставьте её набор и уберите строку плагина. Шаблоны и примеры
Allure не требуют: чтобы включить его, поставьте набор `allure`, добавьте плагин
`qa_core.pytest_plugins.allure_reporting` и запускайте с `--alluredir=allure-results`.

## Слои

Слой знает только слои ниже. Адреса, локаторы и SQL в ядро не попадают.

```text
tests / templates / examples   вызывают нижние слои
фикстуры                       общие: pytest_plugins/fixtures.py; узкие: conftest.py рядом с тестом
config.py, secrets.py          настройки (config.yaml) и секреты (env или Vault)
pytest_plugins/                по желанию: logging, allure_reporting, playwright
checks/                        валидация: excel, odata
clients/                       транспорт: http, postgres
```

## Примеры и шаблоны

- [examples/test_01_http.py](examples/test_01_http.py): HTTP-клиент и проектный клиент поверх него.
- [examples/test_02_preconditions.py](examples/test_02_preconditions.py): данные через API, удаление после теста.
- [examples/test_03_ui_page_object.py](examples/test_03_ui_page_object.py): UI с Page Object ([страница](examples/pages/orders_page.py)).
- [templates/](templates/): заготовки API- и UI-теста, работают без Allure.

## Настройки и секреты

`config.yaml` необязателен; секции `http` и `browser` описаны в [config.yaml](config.yaml),
нет секции или файла — действуют значения по умолчанию. Секреты (`SecretStore`) берутся
из переменных окружения или Vault (`SECRETS_SOURCE=env|vault`, переменные `VAULT_*`), имя
окружения для логов — `--qa-environment` или `TEST_ENV`.

## Если не работает

- `No module named ...`: не установлен набор, поставьте нужный extra.
- Браузер не запускается: `python -m playwright install chromium` (в Docker он уже есть).
- Тесты UI пропущены: задайте `EXAMPLE_UI=1` (только примеры; в Docker уже задано).
- `docker: command not found`: запустите Docker Desktop.

Перед пушем ядра: `python -m pytest` и `ruff check .`.
