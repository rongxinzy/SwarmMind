"""Tests for dialect-aware database configuration."""

from __future__ import annotations

from swarmmind import db


def test_database_url_takes_precedence_over_legacy_db_path(monkeypatch):
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/swarmmind")
    monkeypatch.setenv("SWARMMIND_DB_PATH", "ignored.db")

    assert db._get_database_url() == "postgresql+psycopg://user:pass@localhost:5432/swarmmind"


def test_database_url_falls_back_to_sqlite_path(monkeypatch, tmp_path):
    monkeypatch.delenv("SWARMMIND_DATABASE_URL", raising=False)
    monkeypatch.setattr(db, "DATABASE_URL", None)
    monkeypatch.setenv("SWARMMIND_DB_PATH", str(tmp_path / "fallback.db"))

    resolved = db._get_database_url()

    assert resolved.startswith("sqlite:///")
    assert resolved.endswith("fallback.db")


def test_get_engine_uses_dialect_aware_options(monkeypatch):
    calls: list[tuple[str, dict]] = []
    listens: list[tuple[object, str, object]] = []

    def fake_create_engine(url, **kwargs):
        calls.append((url, kwargs))
        return object()

    def fake_listen(engine, event_name, callback):
        listens.append((engine, event_name, callback))

    monkeypatch.setattr(db, "create_engine", fake_create_engine)
    monkeypatch.setattr(db.event, "listen", fake_listen)
    db.dispose_engines()

    monkeypatch.setenv("SWARMMIND_DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/swarmmind")
    db.get_engine()
    assert calls[-1][0] == "postgresql+psycopg://user:pass@localhost:5432/swarmmind"
    assert calls[-1][1] == {"pool_pre_ping": True}
    assert listens == []

    monkeypatch.setenv("SWARMMIND_DATABASE_URL", "sqlite:////tmp/swarmmind.db")
    db.get_engine()
    assert calls[-1][0] == "sqlite:////tmp/swarmmind.db"
    assert calls[-1][1] == {"pool_pre_ping": True, "connect_args": {"check_same_thread": False}}
    assert listens[-1][1] == "connect"
    assert listens[-1][2] is db._set_sqlite_pragma


def test_get_engine_caches_per_database_url_and_disposes_stale_engines(monkeypatch):
    class FakeEngine:
        def __init__(self, name: str):
            self.name = name
            self.dispose_calls = 0

        def dispose(self):
            self.dispose_calls += 1

    calls: list[str] = []
    created: list[FakeEngine] = []

    def fake_create_engine(url, **_kwargs):
        calls.append(url)
        engine = FakeEngine(url)
        created.append(engine)
        return engine

    monkeypatch.setattr(db, "create_engine", fake_create_engine)
    monkeypatch.setattr(db.event, "listen", lambda *_args, **_kwargs: None)
    db.dispose_engines()

    monkeypatch.setenv("SWARMMIND_DATABASE_URL", "sqlite:////tmp/one.db")
    engine_one = db.get_engine()
    engine_one_again = db.get_engine()

    assert engine_one is engine_one_again
    assert calls == ["sqlite:////tmp/one.db"]

    monkeypatch.setenv("SWARMMIND_DATABASE_URL", "sqlite:////tmp/two.db")
    engine_two = db.get_engine()

    assert engine_two is created[-1]
    assert calls == ["sqlite:////tmp/one.db", "sqlite:////tmp/two.db"]
    assert created[0].dispose_calls == 1


def test_init_db_runs_alembic_migrations(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(db, "run_migrations_to_head", lambda: calls.append("migrate"))

    db.init_db()
    assert calls == ["migrate"]
