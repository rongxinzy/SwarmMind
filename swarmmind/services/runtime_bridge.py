"""Helpers for bridging async runtime execution into sync call sites."""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
from collections.abc import AsyncGenerator, Callable, Generator
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")


def iter_async_generator_in_thread[T](
    async_factory: Callable[[], AsyncGenerator[T, None]],
    *,
    thread_name: str = "runtime-stream",
    join_timeout: float = 5.0,
    bridge_logger: logging.Logger = logger,
) -> Generator[T, None, None]:
    """Run an async generator inside a worker thread and yield its items synchronously."""
    result_queue: queue.Queue[tuple[str, T | None]] = queue.Queue()
    exception_container: list[BaseException] = []
    stop_event = threading.Event()

    async def _drain_async_generator() -> None:
        try:
            async for item in async_factory():
                result_queue.put(("event", item))
        except BaseException as exc:
            exception_container.append(exc)
        finally:
            result_queue.put(("done", None))
            stop_event.set()

    def _run_in_thread() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_drain_async_generator())
        finally:
            try:
                pending = asyncio.all_tasks(loop)
                if pending:
                    for task in pending:
                        task.cancel()
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:  # nosec: B110 - cleanup code, safe to ignore
                pass
            loop.close()

    thread = threading.Thread(target=_run_in_thread, name=thread_name, daemon=True)
    thread.start()

    try:
        while not stop_event.is_set() or not result_queue.empty():
            try:
                item_type, item = result_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if item_type == "done":
                break
            if item_type == "event" and item is not None:
                yield item
    finally:
        thread.join(timeout=join_timeout)
        if thread.is_alive():
            bridge_logger.warning("Async bridge thread %s did not terminate within timeout", thread_name)

    if exception_container:
        raise exception_container[0]


def run_coroutine_blocking[R](
    async_factory: Callable[[], asyncio.Future[R] | asyncio.Awaitable[R]],
    *,
    thread_name: str = "runtime-call",
    join_timeout: float = 5.0,
    bridge_logger: logging.Logger = logger,
) -> R:
    """Run a coroutine to completion from synchronous code.

    If the caller is not already inside an event loop, the coroutine runs
    directly via ``asyncio.run``. When a loop is already active in the current
    thread, execution is isolated in a dedicated worker thread with its own
    event loop.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(async_factory())

    result_queue: queue.Queue[tuple[str, R | BaseException]] = queue.Queue()

    def _run_in_thread() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result_queue.put(("result", loop.run_until_complete(async_factory())))
        except BaseException as exc:
            result_queue.put(("error", exc))
        finally:
            try:
                pending = asyncio.all_tasks(loop)
                if pending:
                    for task in pending:
                        task.cancel()
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:  # nosec: B110 - cleanup code, safe to ignore
                pass
            loop.close()

    thread = threading.Thread(target=_run_in_thread, name=thread_name, daemon=True)
    thread.start()

    try:
        item_type, payload = result_queue.get()
    finally:
        thread.join(timeout=join_timeout)
        if thread.is_alive():
            bridge_logger.warning("Async bridge thread %s did not terminate within timeout", thread_name)

    if item_type == "error":
        raise payload

    return payload
