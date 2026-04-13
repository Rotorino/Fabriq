---
sidebar_position: 6
title: Полное приложение
---

# Полное приложение

Проект собран как единое Python-приложение с модульной архитектурой:

```text
app/            CLI-точка входа
domain/         общие сущности и enum
engine/         дискретно-событийное ядро
scenario/       загрузка, валидация и сборка сценариев
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

Доступные сценарии:

- `configs/base_scenario.json`;
- `configs/high_load.json`;
- `configs/frequent_breakdowns.json`.

## Выходные файлы

Результаты сохраняются в `results/<scenario_name>/`:

- `report.json` - полный отчет;
- `metrics.csv` - таблица метрик;
- `summary.txt` - краткая сводка;
- `charts/queue_length.svg` - длина очереди по времени;
- `charts/machine_utilization.svg` - загрузка станков;
- `charts/batch_cycle_time.svg` - время прохождения партий.

Логи приложения и ядра сохраняются в `logs/`.

## Проверка

```bash
python -m unittest discover -s tests
python -m compileall app domain scenario engine analytics reporting visualization tests
```
