import asyncio
import logging

logger = logging.getLogger("mozhou")


class SimpleEventBus:
    def __init__(self):
        self._handlers: dict[str, list] = {}

    def on(self, event_type: str, handler):
        self._handlers.setdefault(event_type, []).append(handler)

    async def emit(self, event_type: str, payload):
        for handler in self._handlers.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(payload)
                else:
                    handler(payload)
            except Exception as e:
                logger.error("Event handler error for %s: %s", event_type, e)
