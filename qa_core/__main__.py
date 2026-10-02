"""Запуск ``python -m qa_core`` без установки команды ``qa-core``."""

import sys

from qa_core.cli import main

sys.exit(main())
