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

# Global bridge loop — shared across all runtime bridge calls.
# Using a single long-lived event loop avoids "Event loop is closed" errors
# caused by cached async primitives (e.g. httpx.AsyncClient inside
# langchain_anthropic) binding to a loop that gets closed after each request.
_bridge_loop: asyncio.AbstractEventLoop | None = None
_bridge_loop_thread: threading.Thread | None = None
_bridge_loop_lock = threading.Lock()


def _ensure_bridge_loop() -> asyncio.AbstractEventLoop:
    """Return the global bridge event loop, creating it if necessary."""
    global _bridge_loop, _bridge_loop_thread  # noqa: PLW0603
    with _bridge_loop_lock:
        if _bridge_loop is None or _bridge_loop_thread is None or not _bridge_loop_thread.is_alive():
            _bridge_loop = asyncio.new_event_loop()

            def _run_loop() -> None:
                asyncio.set_event_loop(_bridge_loop)
                _bridge_loop.run_forever()

            _bridge_loop_thread = threading.Thread(target=_run_loop, name="runtime-bridge-loop", daemon=True)
            _bridge_loop_thread.start()
        return _bridge_loop


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

    try:
        caller_loop = asyncio.get_running_loop()
    except RuntimeError:
        caller_loop = None

    if caller_loop is None:
        # No running loop — we can run directly in a temporary thread without
        # worrying about cached clients binding to a short-lived loop.
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
                asyncio.set_event_loop(None)

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
        return

    # There is a running loop in the caller thread.
    # Submit the async generator to the shared global bridge loop so that
    # any cached async primitives (httpx client, etc.) bind to a long-lived
    # loop rather than a per-request temporary one.
    bridge_loop = _ensure_bridge_loop()
    future = asyncio.run_coroutine_threadsafe(_drain_async_generator(), bridge_loop)

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
        if not future.done():
            future.cancel()
            # Give the bridge loop a chance to process the cancellation.
            # A tiny sleep is enough because the loop runs in its own thread.
            # We use a threading event to avoid a hard sleep when possible.
            cancelled_event = threading.Event()
            bridge_loop.call_soon_threadsafe(cancelled_event.set)
            cancelled_event.wait(timeout=0.5)

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
    thread, execution is isolated in the shared global bridge loop so that
    cached async primitives remain valid across requests.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(async_factory())

    bridge_loop = _ensure_bridge_loop()
    future = asyncio.run_coroutine_threadsafe(async_factory(), bridge_loop)

    try:
        return future.result(timeout=join_timeout)
    except TimeoutError as exc:
        future.cancel()
        bridge_logger.warning("Async bridge call did not complete within timeout")
        raise TimeoutError("Async bridge call timed out") from exc
