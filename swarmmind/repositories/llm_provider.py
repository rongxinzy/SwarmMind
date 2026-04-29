"""LLM provider repository."""

from __future__ import annotations

import json
import uuid

from sqlalchemy import func
from sqlmodel import select

from swarmmind.db import session_scope
from swarmmind.db_models import LlmProviderDB, LlmProviderModelDB
from swarmmind.models import LlmProvider, LlmProviderDetail, LlmProviderModelEntry
from swarmmind.time_utils import utc_now
from swarmmind.utils.crypto import decrypt, encrypt


class LlmProviderRepository:
    """Repository for LLM provider operations."""

    @staticmethod
    def _mask_api_key(key: str | None) -> str | None:
        """Mask an API key for display (keep first 6 and last 4 chars)."""
        if not key or len(key) <= 12:
            return "***"
        return f"{key[:6]}...{key[-4:]}"

    def create(
        self,
        name: str,
        provider_type: str,
        api_key: str,
        base_url: str | None = None,
        is_default: bool = False,
        models: list[LlmProviderModelEntry] | None = None,
    ) -> LlmProviderDetail:
        """Create a new LLM provider with optional models."""
        provider_id = str(uuid.uuid4())
        now = utc_now()

        with session_scope() as session:
            # If setting as default, unset other defaults
            if is_default:
                existing_defaults = session.exec(
                    select(LlmProviderDB).where(LlmProviderDB.is_default == 1),
                ).all()
                for p in existing_defaults:
                    p.is_default = 0

            db_provider = LlmProviderDB(
                provider_id=provider_id,
                name=name,
                provider_type=provider_type,
                api_key_encrypted=encrypt(api_key),
                base_url=base_url,
                is_enabled=1,
                is_default=1 if is_default else 0,
                created_at=now,
                updated_at=now,
            )
            session.add(db_provider)

            if models:
                for m in models:
                    db_model = LlmProviderModelDB(
                        provider_id=provider_id,
                        model_name=m.model_name,
                        litellm_model=m.litellm_model,
                        display_name=m.display_name,
                        supports_vision=1 if m.supports_vision else 0,
                        supports_thinking=1 if m.supports_thinking else 0,
                        fallback_model_names=json.dumps(m.fallback_model_names) if m.fallback_model_names else None,
                        is_enabled=1,
                        created_at=now,
                    )
                    session.add(db_model)

            session.commit()
            session.refresh(db_provider)
            return self._to_detail(db_provider)

    def get_by_id(self, provider_id: str) -> LlmProviderDetail | None:
        """Fetch a provider by ID with its models."""
        with session_scope() as session:
            db_provider = session.get(LlmProviderDB, provider_id)
            if db_provider is None:
                return None
            return self._to_detail(db_provider)

    def list_all(self, include_disabled: bool = False) -> list[LlmProvider]:
        """List all providers."""
        with session_scope() as session:
            query = select(LlmProviderDB)
            if not include_disabled:
                query = query.where(LlmProviderDB.is_enabled == 1)
            query = query.order_by(LlmProviderDB.created_at.desc())
            results = session.exec(query).all()
            return [self._to_provider(r) for r in results]

    def update(
        self,
        provider_id: str,
        name: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        is_enabled: bool | None = None,
        is_default: bool | None = None,
        models: list[LlmProviderModelEntry] | None = None,
    ) -> LlmProviderDetail | None:
        """Update a provider and optionally replace its model list."""
        with session_scope() as session:
            db_provider = session.get(LlmProviderDB, provider_id)
            if db_provider is None:
                return None

            if name is not None:
                db_provider.name = name
            if api_key is not None:
                db_provider.api_key_encrypted = encrypt(api_key)
            if base_url is not None:
                db_provider.base_url = base_url
            if is_enabled is not None:
                db_provider.is_enabled = 1 if is_enabled else 0
            if is_default is not None:
                if is_default:
                    existing_defaults = session.exec(
                        select(LlmProviderDB).where(
                            LlmProviderDB.is_default == 1,
                            LlmProviderDB.provider_id != provider_id,
                        ),
                    ).all()
                    for p in existing_defaults:
                        p.is_default = 0
                db_provider.is_default = 1 if is_default else 0

            db_provider.updated_at = utc_now()

            if models is not None:
                # Replace existing models
                existing = session.exec(
                    select(LlmProviderModelDB).where(
                        LlmProviderModelDB.provider_id == provider_id,
                    ),
                ).all()
                for m in existing:
                    session.delete(m)

                for m in models:
                    db_model = LlmProviderModelDB(
                        provider_id=provider_id,
                        model_name=m.model_name,
                        litellm_model=m.litellm_model,
                        display_name=m.display_name,
                        supports_vision=1 if m.supports_vision else 0,
                        supports_thinking=1 if m.supports_thinking else 0,
                        fallback_model_names=json.dumps(m.fallback_model_names) if m.fallback_model_names else None,
                        is_enabled=1,
                        created_at=utc_now(),
                    )
                    session.add(db_model)

            session.commit()
            session.refresh(db_provider)
            return self._to_detail(db_provider)

    def delete(self, provider_id: str) -> bool:
        """Soft-disable a provider."""
        with session_scope() as session:
            db_provider = session.get(LlmProviderDB, provider_id)
            if db_provider is None:
                return False
            db_provider.is_enabled = 0
            db_provider.updated_at = utc_now()
            return True

    def get_default_provider(self) -> LlmProviderDetail | None:
        """Fetch the default provider."""
        with session_scope() as session:
            result = session.exec(
                select(LlmProviderDB).where(
                    LlmProviderDB.is_default == 1,
                    LlmProviderDB.is_enabled == 1,
                ),
            ).first()
            if result is None:
                return None
            return self._to_detail(result)

    def get_enabled_providers_with_models(self) -> list[LlmProviderDetail]:
        """Fetch all enabled providers with their models (for Gateway use)."""
        with session_scope() as session:
            providers = session.exec(
                select(LlmProviderDB).where(LlmProviderDB.is_enabled == 1),
            ).all()
            return [self._to_detail(p) for p in providers]

    def get_decrypted_key(self, provider_id: str) -> str | None:
        """Get decrypted API key for a provider (Gateway internal use only)."""
        with session_scope() as session:
            db_provider = session.get(LlmProviderDB, provider_id)
            if db_provider is None:
                return None
            return decrypt(db_provider.api_key_encrypted)

    def count(self) -> int:
        """Total number of providers."""
        with session_scope() as session:
            return session.exec(
                select(func.count(LlmProviderDB.provider_id)),
            ).one()

    @staticmethod
    def _to_provider(db: LlmProviderDB) -> LlmProvider:
        return LlmProvider(
            provider_id=db.provider_id,
            name=db.name,
            provider_type=db.provider_type,  # type: ignore[arg-type]
            base_url=db.base_url,
            is_enabled=bool(db.is_enabled),
            is_default=bool(db.is_default),
            created_at=str(db.created_at) if db.created_at else "",
            updated_at=str(db.updated_at) if db.updated_at else "",
        )

    def _to_detail(self, db: LlmProviderDB) -> LlmProviderDetail:
        with session_scope() as session:
            db_models = session.exec(
                select(LlmProviderModelDB).where(
                    LlmProviderModelDB.provider_id == db.provider_id,
                    LlmProviderModelDB.is_enabled == 1,
                ),
            ).all()
            models = [
                LlmProviderModelEntry(
                    model_name=m.model_name,
                    litellm_model=m.litellm_model,
                    display_name=m.display_name,
                    supports_vision=bool(m.supports_vision),
                    supports_thinking=bool(m.supports_thinking),
                    fallback_model_names=json.loads(m.fallback_model_names) if m.fallback_model_names else [],
                )
                for m in db_models
            ]

        provider = self._to_provider(db)
        return LlmProviderDetail(
            **provider.model_dump(),
            models=models,
        )
