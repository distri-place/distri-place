from __future__ import annotations

import asyncio


class AsyncTicker:
    def __init__(self, interval: float, callback: callable = None, start: bool = None):
        self.interval = interval
        self.callback = callback
        self._loop_task: asyncio.Task | None = None
        self._cb_task: asyncio.Task | None = None
        if self.callback and (start or start is None):
            self.start()

    async def _run(self):
        while True:
            try:
                await asyncio.sleep(self.interval)
                if not self.callback:
                    continue
                result = self.callback()
                if asyncio.iscoroutine(result):
                    self._cb_task = asyncio.create_task(result)
                    self._cb_task.add_done_callback(lambda _: setattr(self, "_cb_task", None))
            except asyncio.CancelledError:
                return

    def start(self, interval: float = None, callback: callable = None):
        if self._loop_task:
            if not self._loop_task.done():
                self._loop_task.cancel()
        self.interval = interval or self.interval
        self.callback = callback or self.callback
        self._loop_task = asyncio.create_task(self._run())

    async def stop(self):
        if self._loop_task:
            self._loop_task.cancel()
            self._loop_task = None
        if self._cb_task:
            await self._cb_task
            self._cb_task = None

    async def reset(self, interval: float = None, callback: callable = None):
        await self.stop()
        self.interval = interval or self.interval
        self.callback = callback or self.callback
        self.start()
