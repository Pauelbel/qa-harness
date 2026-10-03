# Образ для запуска тестов без установки Python и браузеров на компьютер.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONIOENCODING=utf-8 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    EXAMPLE_UI=1

WORKDIR /work

# Зависимости берутся из pyproject.toml (все наборы, кроме dev). Пока pyproject.toml
# не менялся, этот слой берётся из кэша, и браузер заново не скачивается.
COPY pyproject.toml ./
RUN python -c "import tomllib; p = tomllib.load(open('pyproject.toml', 'rb'))['project']; extras = p['optional-dependencies']; print('\n'.join(p['dependencies'] + [d for k, v in extras.items() if k != 'dev' for d in v]))" > /tmp/requirements.txt \
    && pip install -r /tmp/requirements.txt \
    && playwright install --with-deps chromium

COPY . .

CMD ["pytest"]
