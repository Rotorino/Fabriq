# Fabriq

Fabriq — это модульное Python-приложение для дискретно-событийного моделирования
производственной линии. Оно загружает JSON- или YAML-сценарий, строит
валидированную модель производства, запускает движок симуляции, вычисляет
метрики, экспортирует отчёты и создаёт SVG-графики.

## Архитектура

Модули проекта:

- `domain/`: общие сущности, перечисления и DTO
- `scenario/`: загрузка конфигурации, валидация и построение сценариев
- `engine/`: ядро дискретно-событийной симуляции
- `analytics/`: метрики и логика сравнения
- `reporting/`: экспорт отчётов в JSON/CSV/TXT
- `visualization/`: генерация SVG-графиков
- `app/`: CLI-точка входа

Подробная документация находится в `docs/docs/`:

- `architecture.md`: структура движка и правила выполнения
- `event-flow.md`: жизненный цикл событий и условия остановки
- `scenario-module.md`: формат конфигурации, валидация и сборщик сценариев
- `integration-contract.md`: публичные DTO и контракты модулей

## Запуск

### Веб-интерфейс (рекомендуется)

```bash
pip install -r requirements.txt
streamlit run app/ui.py
```

### CLI

```bash
python -m app.main --config configs/base_scenario.json
```


Результаты сохраняются в `results/<scenario_name>/`:

* `report.json`
* `metrics.csv`
* `summary.txt`
* `charts/queue_length.svg`
* `charts/machine_utilization.svg`
* `charts/batch_cycle_time.svg`

При передаче нескольких конфигураций отчёт сравнения сохраняется в
`results/comparison/`:

* `comparison_report.json`
* `comparison.csv`
* `comparison_summary.txt`

Логи сохраняются в `logs/`.

## Сценарии

Репозиторий включает три обязательных сценария:

* `configs/base_scenario.json`
* `configs/high_load.json`
* `configs/frequent_breakdowns.json`

Правила конфигурации, которые важно учитывать:

* JSON обязателен; YAML работает при установленном `PyYAML`.
* `batches.route` обязателен, если линия имеет несколько входных этапов.
* `queue_limit` и `buffer_capacity` должны быть неотрицательными целыми числами или `null`.
* вероятности, такие как `breakdown_probability` и `reject_probability`, должны находиться в диапазоне `[0.0, 1.0]`.

## Тесты

```bash
python -m unittest discover -s tests
python -m pytest -q
python -m compileall app domain scenario engine analytics reporting visualization tests
```

## CI

GitHub Actions запускает Python CI при push и pull request в основные ветки
проекта. Workflow компилирует Python-пакеты, запускает поиск `unittest`,
выполняет `pytest`, прогоняет каждый сценарий `configs/*.json` через CLI,
проверяет повторяемость движка с фиксированным seed и загружает артефакты
`logs/` и `results/`.
