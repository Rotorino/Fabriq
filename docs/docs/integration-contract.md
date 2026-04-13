---
sidebar_position: 4
title: Контракт интеграции
---

# Контракт интеграции

Ядро принимает готовые объекты от модуля сценариев. Оно не создает доменные сущности самостоятельно, поэтому между модулями должен быть согласован минимальный контракт полей.

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

`route` содержит список идентификаторов этапов. Если `route` не задан, ядро использует порядок этапов в `production_line`.

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

## `Stage`

Этап должен предоставлять поля:

```python
stage_id: str
machines: list[Machine]
queue_limit: int | None
reject_probability: float
next_stage_id: str | None
```

Если у этапа есть поле `queue`, ядро использует его как рабочую очередь. Если поля нет, очередь хранится во внутреннем `raw_data`.

```python
queue: list[str]
```

## `ProductionLine`

Производственная линия может быть объектом с полем `stages`, словарем или списком этапов.

Рекомендуемый формат:

```python
class ProductionLine:
    stages: dict[str, Stage]
```

## Статусы

Ядро поддерживает строковые статусы и enum-статусы. Если поле `status` является `Enum`, ядро пытается установить значение через `value`, затем через имя enum в верхнем регистре.

Используемые значения:

```text
idle
busy
broken
waiting
processing
completed
rejected
```

Разработчику модуля `domain` рекомендуется согласовать enum так, чтобы эти значения совпадали с `value`.
