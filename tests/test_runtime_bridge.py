"""Tests for async-to-sync runtime bridge helpers."""

from __future__ import annotations

import asyncio

from swarmmind.services.runtime_bridge import iter_async_generator_in_thread, run_coroutine_blocking


def test_iter_async_generator_in_thread_yields_items_in_order() -> None:
    async def factory():
        yield "first"
        yield "second"

    assert list(iter_async_generator_in_thread(factory, thread_name="bridge-test")) == ["first", "second"]


def test_iter_async_generator_in_thread_reraises_async_errors() -> None:
    async def factory():
        raise RuntimeError("bridge failed")
        yield  # pragma: no cover

    iterator = iter_async_generator_in_thread(factory, thread_name="bridge-test")

    try:
        next(iterator)
    except RuntimeError as exc:
        assert str(exc) == "bridge failed"
    else:  # pragma: no cover
        raise AssertionError("RuntimeError was not re-raised")


def test_run_coroutine_blocking_returns_result_without_existing_loop() -> None:
    async def factory() -> str:
        return "done"

    assert run_coroutine_blocking(factory, thread_name="bridge-call") == "done"


def test_run_coroutine_blocking_uses_worker_thread_when_loop_is_active() -> None:
    async def exercise() -> str:
        async def factory() -> str:
            await asyncio.sleep(0)
            return "done"

        return run_coroutine_blocking(factory, thread_name="bridge-call")

    assert asyncio.run(exercise()) == "done"
