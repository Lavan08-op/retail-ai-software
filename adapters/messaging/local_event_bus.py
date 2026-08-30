"""In-process MessageBus — lets the whole pipeline run and be tested with
zero RabbitMQ dependency during development. RabbitMQBus implements the
same Protocol later and is swapped in without touching any publisher or
subscriber code."""

from collections import defaultdict
from typing import Callable


class LocalEventBus:
    """Implements the MessageBus Protocol. Synchronous, in-memory pub/sub —
    publish() calls every registered handler for that topic immediately,
    in the same thread. Fine for development/testing; a real deployment
    might want this async, but that's an implementation detail behind the
    same interface."""

    def __init__(self):
        self._handlers: dict[str, list[Callable[[dict], None]]] = defaultdict(list)

    def publish(self, topic: str, payload: dict) -> None:
        for handler in self._handlers.get(topic, []):
            handler(payload)

    def subscribe(self, topic: str, handler: Callable[[dict], None]) -> None:
        self._handlers[topic].append(handler)
