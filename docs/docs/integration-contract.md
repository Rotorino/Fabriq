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

## Контракт Матвея Струцкого -> Никиты Горбаткова

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

Если у линии несколько входных этапов, `route` становится обязательным. Ядро не должно угадывать, с какого входа должна стартовать партия.

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

Если у этапа есть поле `buffer`, ядро использует его как рабочий буфер для партий, которые не помещаются в очередь. В текущей реализации `domain.Stage.buffer` хранит объект `Buffer`. Если поля нет, буфер хранится во внутреннем `raw_data`.

```python
buffer: Buffer
```

`buffer_capacity` задает максимальное число партий в буфере. Значение `None` означает неограниченный буфер, `0` означает отсутствие буфера.

Рекомендуемая модель буфера:

```python
class Buffer:
    capacity: int | None
    batch_ids: list[str]
```

- `capacity is None` - буфер не ограничен;
- `capacity == 0` - буфер отключен;
- `capacity > 0` - допускается не более `capacity` партий;
- рабочее содержимое буфера находится в `batch_ids`.

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
    entry_stage_ids: list[str]
```

`entry_stage_id` вычисляется модулем сценариев при сборке линии и фиксирует логический вход в простой линейной цепочке.
`entry_stage_ids` содержит все допустимые входные этапы линии и нужен для сценариев с несколькими входами.

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

## Контракт Никиты Горбаткова -> Тимура Несмашного

`SimulationResult` после сегодняшних правок имеет следующий публичный вид:

```python
@dataclass(slots=True)
class SimulationResult:
    events: list[Event]
    event_log: list[EventLogRecord]
    batches: list[Batch]
    stages: list[Stage]
    machines: list[Machine]
    simulation_time: float
    scenario_name: str
    raw_data: dict[str, Any]
```

- `events` - сырые обработанные события движка;
- `event_log` - журнал результатов обработки, который использует аналитика;
- `raw_data` - технические ряды по очередям, буферам и активности станков.

Структура `raw_data`:

```python
raw_data = {
    "queue_lengths": list[dict[str, float | int | str]],
    "buffer_lengths": list[dict[str, float | int | str]],
    "machine_activity": list[dict[str, float | str | None]],
}
```

`queue_lengths` содержит наблюдения длины очереди:

```python
{
    "timestamp": 5.0,
    "stage_id": "assembly",
    "queue_length": 2,
}
```

`buffer_lengths` содержит наблюдения длины буфера:

```python
{
    "timestamp": 5.0,
    "stage_id": "assembly",
    "buffer_length": 1,
}
```

`machine_activity` содержит технический журнал смены состояний станка:

```python
{
    "timestamp": 5.0,
    "machine_id": "asm-1",
    "event": "processing_started",
    "batch_id": "batch-3",
}
```

Все три ряда являются публичной частью контракта Никиты Горбаткова -> Тимура Несмашного. Аналитика не должна читать внутренние ключи `raw_data`, начинающиеся с `_`.

Property `processed_events` сохранен только как совместимый alias для уже написанного кода аналитики.

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
