---
sidebar_position: 6
title: Полное приложение
---

# Полное приложение

Проект собран как единое Python-приложение с модульной архитектурой:

```text
app/            CLI-точка входа
domain/         общие сущности, enum и DTO
scenario/       загрузка JSON/YAML, валидация и сборка сценариев
engine/         дискретно-событийное ядро
analytics/      расчет метрик
reporting/      экспорт JSON, CSV и TXT
visualization/  SVG-графики
configs/        три демонстрационных сценария
tests/          unit- и интеграционные тесты
```

## Запуск

```bash
python -m app.main --config configs/base_scenario.json
```

CLI также поддерживает сравнение нескольких сценариев одной командой:

```bash
python -m app.main --config \
  configs/base_scenario.json \
  configs/high_load.json \
  configs/frequent_breakdowns.json
```

Доступные сценарии:

- `configs/base_scenario.json`;
- `configs/high_load.json`;
- `configs/frequent_breakdowns.json`.

Поддерживаемые форматы конфигураций:

- `JSON`;
- `YAML`;
- `YML`.

Сценарный слой отдает в ядро объект `ScenarioInput`, включающий:

- `production_line`;
- `batches`;
- `scenario_config`.

## Выходные файлы

Результаты сохраняются в ``results/<scenario_name>/``:

- `report.json` - полный отчет;
- `metrics.csv` - таблица метрик;
- `summary.txt` - краткая сводка;
- `charts/queue_length.svg` - длина очереди по времени;
- `charts/machine_utilization.svg` - загрузка станков;
- `charts/batch_cycle_time.svg` - время прохождения партий.

Если передано несколько конфигураций, дополнительно создается каталог `results/comparison/`:

- `comparison_report.json` - полный сравнительный отчет;
- `comparison.csv` - агрегированная таблица сравнения;
- `comparison_summary.txt` - краткая текстовая сводка.

Логи приложения и ядра сохраняются в `logs/`.

## Что изменилось сегодня

В текущей версии приложение дополнительно поддерживает:

- корректный публичный контракт `SimulationResult` с разделением `events` и `event_log`;
- защиту движка от зависания на нулевых длительностях обработки;
- несколько входных этапов линии при явном маршруте партии;
- автоматическое сравнение сценариев на уровне CLI и reporting;
- расширенные отчеты с bottleneck, problem stages и comparison summary.

## Проверка

```bash
python -m unittest discover -s tests
python -m compileall app domain scenario engine analytics reporting visualization tests
```

Отдельная проверка сценарного слоя:

```bash
python -m unittest tests.test_scenario
```
