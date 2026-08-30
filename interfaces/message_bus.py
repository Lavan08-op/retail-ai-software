"""MessageBus contract. LocalEventBus (mine, in-process, used during
development) and RabbitMQBus (mine too, but only wired in once RabbitMQ is
actually running) both implement this — nothing else in the system should
care which one is active."""

from typing import Callable, Protocol


class MessageBus(Protocol):
    def publish(self, topic: str, payload: dict) -> None: ...

    def subscribe(self, topic: str, handler: Callable[[dict], None]) -> None: ...
