# qa-harness

Личный QA-фреймворк на Python и pytest. Клонируете репозиторий и работаете прямо в нём:
ядро `qa_core/` лежит рядом с тестами, обновляется через `git pull`. Правила тестов — в [Правила.md](Правила.md).

## Быстрый старт

Нужны Python 3.11+ и Git.

```bash
git clone https://github.com/Pauelbel/qa-harness.git
cd qa-harness
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
python -m pytest
```

Части тестов запускаются по маркерам `api`, `ui`, `db`, `smoke`: `python -m pytest -m smoke`.

## Слои

Слой знает только слои ниже. Адреса, локаторы и SQL в ядро не попадают.

```text
tests/, examples/, templates/   тесты и заготовки: только вызывают нижние слои
фикстуры                        общие: pytest_plugins/fixtures.py; узкие: conftest.py рядом с тестом
pytest_plugins/                 по желанию: logging, allure_reporting, playwright
checks/                         проверки: excel, odata (позже json, xml)
clients/                        транспорт: http, postgres, browser (BasePage/BaseElement)
                                (позже websocket и др.)
sources/                        подготовка данных для проверок (Excel из файла или ответа)
config.py, secrets.py, steps.py настройки (config.py), секреты (env или Vault),
                                шаг теста: лог, а при наличии Allure ещё и шаг отчёта
```

Новый клиент или проверка — новый файл в `clients/` или `checks/`. Плагин подключается
строкой в `conftest.py`:

```python
pytest_plugins = [
    "qa_core.pytest_plugins.fixtures",    # маркеры и фикстура http_client
    "qa_core.pytest_plugins.logging",     # логи в консоль и logs/
    "qa_core.pytest_plugins.playwright",  # browser_page, скриншот и trace при падении
]
```

## Маркеры

| Маркер | Что помечает | Запуск |
| --- | --- | --- |
| `api` | тесты HTTP/API | `python -m pytest -m api` |
| `ui` | тесты в браузере | `python -m pytest -m ui` |
| `db` | тесты с базой данных | `python -m pytest -m db` |
| `smoke` | быстрая проверка, что система жива | `python -m pytest -m smoke` |

Можно комбинировать: `-m "api and smoke"`, `-m "not ui"`. Неизвестный маркер даёт ошибку.

## Новый тест

Скопируйте [шаблон](templates/) в `tests/`, замените адрес и данные (места помечены
«ЗАМЕНИТЕ»). Образец UI-теста с данными через API и Page Object — в [examples/](examples/).

## Allure

Шаблоны и примеры работают без Allure. Чтобы включить: плагин
`qa_core.pytest_plugins.allure_reporting` в `conftest.py` и ключ `--alluredir=allure-results`.

## Ядро на другом проекте

Ядро не ставится как пакет: оно просто лежит папкой. Чтобы взять его на другой проект и потом
обновлять, подключите репозиторий как `git subtree`:

```bash
git subtree add  --prefix=qa-harness https://github.com/Pauelbel/qa-harness.git main --squash
git subtree pull --prefix=qa-harness https://github.com/Pauelbel/qa-harness.git main --squash   # обновить
git subtree push --prefix=qa-harness https://github.com/Pauelbel/qa-harness.git main            # отправить правку ядра
```

В `pytest.ini` проекта укажите `pythonpath = qa-harness`, зависимости берите из
`qa-harness/requirements.txt`. Правки ядра делайте так, чтобы они подходили всем проектам.

## Дальше

- [examples/](examples/): HTTP, предусловие через API, UI с Page Object.
- [templates/](templates/): заготовки API- и UI-теста, копируйте и меняйте.
- Настройки — `config.py` (необязателен), секреты — переменные окружения или Vault.
- Перед пушем: `python -m pytest`.
