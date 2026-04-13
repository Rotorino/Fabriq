---
sidebar_position: 2
title: Архитектура ядра
---

# Архитектура ядра

Ядро построено как набор небольших модулей. Каждый модуль имеет отдельную ответственность и может использоваться независимо в тестах.

## `events.py`

Модуль содержит DTO события и enum типов событий.

`Event` включает:

- `event_id`;
- `timestamp`;
- `event_type`;
- `batch_id`;
- `stage_id`;
- `machine_id`;
- `payload`.

Поддерживаемые типы событий:

```text
BATCH_ARRIVAL
QUEUE_ENTER
PROCESSING_START
PROCESSING_FINISH
MOVE_TO_NEXT_STAGE
MACHINE_BREAKDOWN
REPAIR_FINISH
BATCH_REJECTED
SIMULATION_END
```

## `event_queue.py`

`EventQueue` реализует стабильную приоритетную очередь на базе `heapq`.

Очередь сортирует события по `timestamp`. Если несколько событий имеют одинаковое время, они извлекаются в порядке добавления. Это важно для воспроизводимости симуляции.

## `context.py`

`SimulationContext` хранит изменяемое состояние выполнения:

- текущее время;
- очередь событий;
- производственную линию;
- партии;
- журнал событий;
- служебные данные для аналитики;
- флаг остановки.

`EventLogRecord` хранит результат обработки одного события:

- время;
- тип события;
- партию;
- этап;
- станок;
- результат действия;
- дополнительные детали.

## `dispatcher.py`

`EventDispatcher` получает событие и вызывает обработчик по типу события:

```python
handler = handlers[event.event_type]
handler.handle(event, context)
```

Если обработчик не зарегистрирован, диспетчер выбрасывает ошибку с понятным сообщением.

## `handlers.py`

Модуль содержит обработчики событий и вспомогательные функции для работы с очередями, статусами, станками и маршрутами.

Ключевые обработчики:

- `BatchArrivalHandler`;
- `QueueEnterHandler`;
- `ProcessingStartHandler`;
- `ProcessingFinishHandler`;
- `MoveToNextStageHandler`;
- `MachineBreakdownHandler`;
- `RepairFinishHandler`;
- `BatchRejectedHandler`;
- `SimulationEndHandler`.

## `simulator.py`

`SimulationEngine` является основной точкой входа в ядро. Он создает контекст, планирует начальные события, запускает цикл обработки и возвращает `SimulationResult`.

`SimulationResult` содержит:

- журнал событий;
- итоговые партии;
- итоговые этапы;
- итоговые станки;
- время симуляции;
- имя сценария;
- сырые технические данные.
