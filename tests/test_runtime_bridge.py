"""Tests for async-to-sync runtime bridge helpers."""

from __future__ import annotations

from swarmmind.services.runtime_bridge import iter_async_generator_in_thread


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
