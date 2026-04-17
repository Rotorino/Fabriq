---
sidebar_position: 4
title: Контракт интеграции
---

# Контракт интеграции

Ядро принимает готовые объекты от модуля сценариев. Оно не создает доменные сущности самостоятельно, поэтому между модулями должен быть согласован минимальный контракт полей.

`SimulationEngine.run()` работает с копиями переданных объектов. Это позволяет безопасно запускать один и тот же сценарий несколько раз: исходные партии, этапы, очереди, буферы и станки не сохраняют состояние предыдущего прогона. Итоговое состояние для аналитики и отчетов находится в `SimulationResult`.

Текущий рекомендуемый входной DTO от модуля сценариев:

```python
@dataclass(slots=True)
class ScenarioInput:
    production_line: ProductionLine
    batches: list[Batch]
    scenario_config: ScenarioConfig
```

## Контракт разработчика 2 -> разработчика 1

Модуль `scenario` должен передать в `engine`:

- валидированный `ProductionLine`;
- список `Batch`;
- согласованные enum и статусы;
- параметры сценария в `ScenarioConfig`.

Ядро использует только публичные поля и не должно обращаться к приватным деталям загрузчика или валидатора.

## `Batch`

Партия должна предоставлять поля:

```python
batch_id: str
arrival_time: float
route: list[str]
current_stage_index: int
status: str | Enum
is_rejected: bool
```

`route` содержит список идентификаторов этапов. Если `route` не задан, модуль сценариев заранее выводит его из `entry_stage_id` и цепочки `next_stage_id`, после чего передает в ядро уже явный маршрут.

Рекомендуемая реализация в проекте:

```python
class Batch:
    batch_id: str
    arrival_time: float
    size: int
    route: list[str]
    current_stage_index: int
    status: BatchStatus
    is_rejected: bool
```

## `Machine`

Станок должен предоставлять поля:

```python
machine_id: str
stage_id: str
status: str | Enum
processing_time: float
breakdown_probability: float
repair_time: float
busy_until: float
```

Дополнительно ядро может синхронизировать поля, если они есть у объекта:

```python
current_batch_id: str | None
interrupted_batch_id: str | None
start_scheduled: bool
```

Рекомендуемая реализация в проекте:

```python
class Machine:
    machine_id: str
    stage_id: str
    processing_time: float
    breakdown_probability: float
    repair_time: float
    status: MachineStatus
    busy_until: float
    current_batch_id: str | None
    interrupted_batch_id: str | None
```

## `Stage`

Этап должен предоставлять поля:

```python
stage_id: str
machines: list[Machine]
queue_limit: int | None
reject_probability: float
next_stage_id: str | None
buffer_capacity: int | None
```

Если у этапа есть поле `queue`, ядро использует его как рабочую очередь. Если поля нет, очередь хранится во внутреннем `raw_data`.

```python
queue: list[str]
```

Если у этапа есть поле `buffer`, ядро использует его как рабочий буфер для партий, которые не помещаются в очередь. Если поля нет, буфер хранится во внутреннем `raw_data`.

```python
buffer: list[str]
```

`buffer_capacity` задает максимальное число партий в буфере. Значение `None` означает неограниченный буфер, `0` означает отсутствие буфера.

Рекомендуемая реализация в проекте:

```python
class Stage:
    stage_id: str
    name: str
    machines: list[Machine]
    queue_limit: int | None
    reject_probability: float
    buffer_capacity: int | None
    next_stage_id: str | None
    stage_type: StageType
    routing_strategy: RoutingStrategy
    queue: list[str]
    buffer: list[str]
```

## `ProductionLine`

Производственная линия может быть объектом с полем `stages`, словарем или списком этапов.

Рекомендуемый формат:

```python
class ProductionLine:
    stages: dict[str, Stage]
    entry_stage_id: str | None
```

`entry_stage_id` вычисляется модулем сценариев при сборке линии и фиксирует логический вход в производственную цепочку.

## `ScenarioConfig`

Сценарный слой дополнительно передает метаданные запуска:

```python
class ScenarioConfig:
    name: str
    description: str
    simulation_duration: float
    seed: int | None
    batch_generation_mode: str
    metadata: dict[str, Any]
```

`ScenarioConfig` нужен для:

- передачи длительности моделирования в `engine`;
- фиксации имени сценария;
- воспроизводимости через `seed`;
- передачи описания в `reporting`;
- сопоставления способа генерации партий в техдокументации и тестах.

## Статусы

Ядро поддерживает строковые статусы и enum-статусы. Если поле `status` является `Enum`, ядро пытается установить значение через `value`, затем через имя enum в верхнем регистре.

Используемые значения:

```text
idle
busy
broken
buffered
waiting
processing
completed
rejected
```

Разработчику модуля `domain` рекомендуется согласовать enum так, чтобы эти значения совпадали с `value`.

В текущей реализации это условие выполнено.
