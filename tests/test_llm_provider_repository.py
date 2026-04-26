"""Tests for LlmProviderRepository."""

from __future__ import annotations

import pytest

from swarmmind.db import init_orm_db
from swarmmind.models import LlmProviderModelEntry
from swarmmind.repositories.llm_provider import LlmProviderRepository


@pytest.fixture(autouse=True)
def _fresh_db(monkeypatch, tmp_path):
    db_path = tmp_path / "llm_provider_repo_test.db"
    monkeypatch.setenv("SWARMMIND_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SWARMMIND_DB_INIT_MODE", "create_all")
    init_orm_db()


@pytest.fixture
def repo():
    return LlmProviderRepository()


def test_create_provider(repo):
    provider = repo.create(
        name="OpenAI Test",
        provider_type="openai",
        api_key="sk-test-openai-key",
        base_url="https://api.openai.com/v1",
        models=[
            LlmProviderModelEntry(
                model_name="gpt-4o",
                litellm_model="openai/gpt-4o",
                supports_vision=True,
            ),
        ],
    )
    assert provider.name == "OpenAI Test"
    assert provider.provider_type == "openai"
    assert provider.base_url == "https://api.openai.com/v1"
    assert provider.is_enabled is True
    assert len(provider.models) == 1
    assert provider.models[0].model_name == "gpt-4o"


def test_create_provider_with_default_flag(repo):
    p1 = repo.create(
        name="Provider 1",
        provider_type="openai",
        api_key="sk-1",
        is_default=True,
    )
    assert p1.is_default is True

    p2 = repo.create(
        name="Provider 2",
        provider_type="anthropic",
        api_key="sk-2",
        is_default=True,
    )
    assert p2.is_default is True

    # p1 should no longer be default
    p1_refreshed = repo.get_by_id(p1.provider_id)
    assert p1_refreshed.is_default is False


def test_get_by_id(repo):
    created = repo.create(name="Test", provider_type="openai", api_key="sk-xxx")
    fetched = repo.get_by_id(created.provider_id)
    assert fetched is not None
    assert fetched.provider_id == created.provider_id
    assert fetched.name == "Test"


def test_get_by_id_not_found(repo):
    assert repo.get_by_id("nonexistent") is None


def test_list_all(repo):
    repo.create(name="A", provider_type="openai", api_key="sk-a")
    repo.create(name="B", provider_type="anthropic", api_key="sk-b")
    items = repo.list_all()
    assert len(items) == 2


def test_list_all_excludes_disabled(repo):
    p = repo.create(name="A", provider_type="openai", api_key="sk-a")
    repo.delete(p.provider_id)
    items = repo.list_all(include_disabled=False)
    assert len(items) == 0
    items = repo.list_all(include_disabled=True)
    assert len(items) == 1
    assert items[0].is_enabled is False


def test_update_provider(repo):
    created = repo.create(name="Old", provider_type="openai", api_key="sk-old")
    updated = repo.update(created.provider_id, name="New")
    assert updated is not None
    assert updated.name == "New"
    # API key should remain unchanged when not provided
    assert repo.get_decrypted_key(created.provider_id) == "sk-old"


def test_update_api_key(repo):
    created = repo.create(name="Test", provider_type="openai", api_key="sk-old")
    repo.update(created.provider_id, api_key="sk-new")
    assert repo.get_decrypted_key(created.provider_id) == "sk-new"


def test_update_models(repo):
    created = repo.create(
        name="Test",
        provider_type="openai",
        api_key="sk-xxx",
        models=[LlmProviderModelEntry(model_name="gpt-4o", litellm_model="openai/gpt-4o")],
    )
    assert len(created.models) == 1

    updated = repo.update(
        created.provider_id,
        models=[
            LlmProviderModelEntry(model_name="gpt-4o", litellm_model="openai/gpt-4o"),
            LlmProviderModelEntry(model_name="gpt-4o-mini", litellm_model="openai/gpt-4o-mini"),
        ],
    )
    assert len(updated.models) == 2


def test_delete_soft_disable(repo):
    created = repo.create(name="Test", provider_type="openai", api_key="sk-xxx")
    ok = repo.delete(created.provider_id)
    assert ok is True
    fetched = repo.get_by_id(created.provider_id)
    assert fetched is not None
    assert fetched.is_enabled is False


def test_delete_not_found(repo):
    assert repo.delete("nonexistent") is False


def test_get_default_provider(repo):
    repo.create(name="A", provider_type="openai", api_key="sk-a")
    default = repo.create(name="B", provider_type="anthropic", api_key="sk-b", is_default=True)

    result = repo.get_default_provider()
    assert result is not None
    assert result.provider_id == default.provider_id


def test_get_default_provider_none(repo):
    assert repo.get_default_provider() is None


def test_get_enabled_providers_with_models(repo):
    repo.create(
        name="OpenAI",
        provider_type="openai",
        api_key="sk-test",
        models=[
            LlmProviderModelEntry(model_name="gpt-4o", litellm_model="openai/gpt-4o"),
        ],
    )
    providers = repo.get_enabled_providers_with_models()
    assert len(providers) == 1
    assert len(providers[0].models) == 1


def test_count(repo):
    assert repo.count() == 0
    repo.create(name="A", provider_type="openai", api_key="sk-a")
    assert repo.count() == 1


def test_encryption_roundtrip(repo):
    repo.create(name="Secret", provider_type="openai", api_key="my-secret-key-12345")
    providers = repo.get_enabled_providers_with_models()
    decrypted = repo.get_decrypted_key(providers[0].provider_id)
    assert decrypted == "my-secret-key-12345"
