"""Runtime model catalog routes."""

from __future__ import annotations

from fastapi import APIRouter

from swarmmind.models import RuntimeModelCatalogResponse, RuntimeModelOption
from swarmmind.runtime.catalog import (
    ANONYMOUS_SUBJECT_ID,
    ANONYMOUS_SUBJECT_TYPE,
    list_models_for_subject,
)


def build_runtime_models_router() -> APIRouter:
    router = APIRouter()

    @router.get("/models", tags=["runtime"])
    @router.get("/runtime/models", tags=["runtime"])
    def list_runtime_models() -> RuntimeModelCatalogResponse:
        """List runtime models available to the current anonymous visitor subject."""
        return _list_runtime_models()

    return router


def list_runtime_models() -> RuntimeModelCatalogResponse:
    """Return the runtime model catalog for the anonymous subject.

    Exposed as a module-level function so supervisor.py can re-export it
    for backward-compatible direct calls in tests.
    """
    return _list_runtime_models()


def _list_runtime_models() -> RuntimeModelCatalogResponse:
    models = list_models_for_subject(
        subject_type=ANONYMOUS_SUBJECT_TYPE,
        subject_id=ANONYMOUS_SUBJECT_ID,
    )
    default_model = next((m.name for m in models if m.is_default), None)
    return RuntimeModelCatalogResponse(
        models=[
            RuntimeModelOption(
                name=m.name,
                provider=m.provider,
                model=m.model,
                display_name=m.display_name,
                description=m.description,
                supports_vision=m.supports_vision,
                supports_thinking=m.supports_thinking,
                capability_tags=m.capability_tags,
                is_default=m.is_default,
            )
            for m in models
        ],
        default_model=default_model,
        subject_type=ANONYMOUS_SUBJECT_TYPE,
        subject_id=ANONYMOUS_SUBJECT_ID,
    )
