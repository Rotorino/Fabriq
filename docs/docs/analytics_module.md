# Документация модуля аналитики

## Обзор

Модуль аналитики отвечает за расчёт показателей производительности на основе результатов симуляции. Он обрабатывает исходные данные симуляции и формирует подробную статистику по партиям, этапам производства, оборудованию и общей эффективности системы.

## Структура модуля

```text
analytics/
├── __init__.py
├── aggregators.py      # Вспомогательные функции агрегации данных
├── calculators.py      # Основная логика расчёта аналитики
└── metrics.py          # Формулы расчёта метрик низкого уровня
```

## Основные функции

### `calculate_analytics(result: SimulationResult) -> dict`

Основная точка входа для расчёта аналитики. Принимает результат симуляции и возвращает словарь с полным набором аналитических данных.

**Возвращает:**

```python
{
    "scenario_name": str,
    "general": {
        "total_batches": int,
        "completed_batches": int,
        "rejected_batches": int,
        "simulation_time": float,
        "output_units": int,
        "rejected_units": int,
        "throughput": float,
        "total_breakdowns": int,
        "total_repair_time": float
    },
    "stages": [StageMetrics, ...],
    "machines": [MachineMetrics, ...],
    "batches": [BatchMetrics, ...]
}
```

### `compare_analytics_runs(analytics_runs: list) -> list`

Сравнивает результаты аналитики нескольких сценариев и формирует таблицу сравнения.

**Возвращает:**

```python
[
    {
        "scenario_name": str,
        "output_units": int,
        "average_cycle_time": float,
        "rejection_rate": float,
        "average_queue_length": float,
        "average_machine_utilization": float,
        "throughput": float,
        "total_breakdowns": int,
        "total_repair_time": float
    },
    ...
]
```

## Описание метрик

### Общие метрики

* **total_batches** — общее количество партий, поступивших в систему.
* **completed_batches** — количество партий, успешно прошедших все этапы производства.
* **rejected_batches** — количество партий, отклонённых из-за проблем с качеством.
* **output_units** — общее количество произведённых единиц продукции (сумма размеров завершённых партий).
* **rejected_units** — общее количество забракованных единиц продукции (сумма размеров отклонённых партий).
* **throughput** — производительность системы (output_units / simulation_time).
* **total_breakdowns** — суммарное количество поломок оборудования в системе.
* **total_repair_time** — общее время, затраченное на ремонт оборудования.

### Метрики этапов производства

* **processed_batches** — количество партий, обработанных на данном этапе.
* **average_wait_time** — среднее время ожидания партии в очереди.
* **average_processing_time** — среднее время непосредственной обработки партии.
* **max_queue_length** — максимальная зафиксированная длина очереди.
* **utilization** — средняя загрузка оборудования на этапе.
* **rejected_batches** — количество партий, отклонённых на данном этапе.
* **breakdowns** — количество поломок оборудования на этапе.

### Метрики оборудования

* **busy_time** — общее время, в течение которого оборудование выполняло обработку.
* **idle_time** — общее время простоя оборудования.
* **breakdowns** — количество поломок данного оборудования.
* **average_repair_time** — среднее время ремонта оборудования.
* **utilization** — отношение времени работы к общей продолжительности симуляции.

### Метрики партий

* **cycle_time** — полное время прохождения партии от поступления до завершения или отклонения.
* **stages_count** — количество этапов в маршруте партии.
* **completed** — логическое значение, указывающее на успешное завершение партии.
* **waited_in_queue** — логическое значение, показывающее, ожидала ли партия в очереди.

## Примеры использования

### Базовый расчёт аналитики

```python
from analytics import calculate_analytics
from engine import SimulationEngine

result = SimulationEngine(
    production_line=line,
    batches=batches,
    simulation_duration=100.0,
    scenario_name="test"
).run()

analytics = calculate_analytics(result)

print(f"Производительность: {analytics['general']['throughput']:.2f} ед./время")
print(
    f"Доля брака: "
    f"{analytics['general']['rejected_batches'] / analytics['general']['total_batches']:.1%}"
)
```

### Сравнение сценариев

```python
from analytics import calculate_analytics, compare_analytics_runs

analytics_runs = []

for config_path in [
    "base.json",
    "high_load.json",
    "frequent_breakdowns.json"
]:
    result = run_simulation(config_path)
    analytics_runs.append(calculate_analytics(result))

comparison = compare_analytics_runs(analytics_runs)

for row in comparison:
    print(
        f"{row['scenario_name']}: "
        f"{row['output_units']} единиц продукции, "
        f"{row['average_cycle_time']:.2f} среднее время цикла"
    )
```

## Особенности производительности

* Расчёт аналитики выполняется после завершения симуляции.
* Потребление памяти растёт линейно относительно количества событий и партий.
* Для крупных симуляций (более 10 000 событий) рекомендуется использовать потоковую аналитику.
* Функции агрегации используют словари для доступа к данным за время O(1).

## Точки интеграции

### Входные данные от модуля движка

Модуль аналитики ожидает объект `SimulationResult`, содержащий:

* `events` — список обработанных событий.
* `event_log` — журнал событий.
* `batches` — список партий с их итоговыми состояниями.
* `stages` — список этапов с их итоговыми состояниями.
* `machines` — список оборудования с их итоговыми состояниями.
* `simulation_time` — общая продолжительность симуляции.
* `raw_data` — словарь с наблюдениями за длиной очередей и активностью оборудования.

### Выходные данные для модуля отчётности

Результаты аналитики используются следующими компонентами:

* `reporting.build_report()` — создание отчёта по одному сценарию.
* `reporting.build_comparison_report()` — создание сравнительного отчёта по нескольким сценариям.
* `visualization.build_charts()` — построение графиков и диаграмм.

## Обработка ошибок

Модуль корректно обрабатывает граничные случаи:

* Пустые списки партий возвращают нулевые значения метрик.
* Деление на ноль предотвращается с помощью защитных конструкций вида `max(value, 1)`.
* Отсутствующие поля заменяются значениями по умолчанию (`0` или пустые списки).
* Некорректные типы данных перехватываются на этапе агрегации.

## Тестирование

Полное покрытие тестами находится в файле `tests/test_analytics.py`.

Основные тесты:

* `test_calculate_analytics_includes_extended_metrics` — проверка всех полей метрик.
* `test_compare_analytics_runs_returns_required_columns` — проверка структуры результатов сравнения.
* `test_analytics_handles_zero_batches` — проверка обработки случая с нулевым количеством партий.

## Будущие улучшения

Возможные направления развития модуля:

* Аналитика в реальном времени во время выполнения симуляции.
* Расчёт доверительных интервалов для метрик.
* Анализ тенденций между несколькими запусками.
* Прогнозирование узких мест с использованием машинного обучения.
* Поддержка пользовательских плагинов метрик.
