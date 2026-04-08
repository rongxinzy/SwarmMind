"""Bootstrap the local DeerFlow Runtime Instance with explicit config injection."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from swarmmind.runtime.catalog import list_enabled_runtime_models, sync_env_runtime_model
from swarmmind.runtime.errors import RuntimeConfigError
from swarmmind.runtime.models import RuntimeInstance, RuntimeModel, RuntimeProfile
from swarmmind.runtime.profile import resolve_default_runtime_profile

logger = logging.getLogger(__name__)

DEFAULT_RUNTIME_INSTANCE_ID = "local-default-instance"


def _runtime_root() -> Path:
    return Path(__file__).resolve().parents[2] / ".runtime" / "deerflow" / "local-default"


def _yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _render_model_lines(model: RuntimeModel) -> list[str]:
    lines = [
        f"  - name: {_yaml_quote(model.name)}",
        f"    display_name: {_yaml_quote(model.display_name or model.name)}",
        f"    use: {_yaml_quote(model.model_class)}",
        f"    model: {_yaml_quote(model.model)}",
        f"    api_key: {_yaml_quote(f'${model.api_key_env_var}')}",
        "    max_tokens: 4096",
    ]
    if model.base_url:
        lines.append(f"    base_url: {_yaml_quote(model.base_url)}")
    if model.supports_vision:
        lines.append("    supports_vision: true")
    return lines


def _render_config(profile: RuntimeProfile, deer_flow_home: Path, models: list[RuntimeModel]) -> str:
    ordered_models = sorted(
        models,
        key=lambda model: (0 if model.name == profile.model_name else 1, model.name),
    )
    lines = [
        "config_version: 3",
        "",
        "models:",
    ]
    for model in ordered_models:
        lines.extend(_render_model_lines(model))

    lines.extend(
        [
            "",
            "tool_groups:",
            "  - name: web",
            "  - name: file:read",
            "  - name: file:write",
            "  - name: bash",
            "",
            "tools:",
            "  - name: web_search",
            "    group: web",
            "    use: deerflow.community.tavily.tools:web_search_tool",
            "    max_results: 5",
            "  - name: web_fetch",
            "    group: web",
            "    use: deerflow.community.jina_ai.tools:web_fetch_tool",
            "    timeout: 10",
            "  - name: image_search",
            "    group: web",
            "    use: deerflow.community.image_search.tools:image_search_tool",
            "    max_results: 5",
            "  - name: ls",
            "    group: file:read",
            "    use: deerflow.sandbox.tools:ls_tool",
            "  - name: read_file",
            "    group: file:read",
            "    use: deerflow.sandbox.tools:read_file_tool",
            "  - name: write_file",
            "    group: file:write",
            "    use: deerflow.sandbox.tools:write_file_tool",
            "  - name: edit_file",
            "    group: file:write",
            "    use: deerflow.sandbox.tools:str_replace_tool",
            "  - name: bash",
            "    group: bash",
            "    use: deerflow.sandbox.tools:bash_tool",
            "",
            "sandbox:",
            "  use: deerflow.sandbox.local:LocalSandboxProvider",
            "",
            "skills: {}",
            "tool_search: {}",
            "",
            "checkpointer:",
            "  type: memory",
            "",
            "memory:",
            f"  storage_path: {_yaml_quote(str(deer_flow_home / 'memory.json'))}",
            "",
            "summarization:",
            "  enabled: false",
        ]
    )
    return "\n".join(lines) + "\n"


def ensure_default_runtime_instance() -> RuntimeInstance:
    """Create and export the single local DeerFlow runtime bundle for MVP use."""
    sync_env_runtime_model()
    profile = resolve_default_runtime_profile()
    runtime_models = list_enabled_runtime_models()
    runtime_root = _runtime_root()
    deer_flow_home = runtime_root / "home"
    config_path = runtime_root / "config.yaml"
    extensions_config_path = runtime_root / "extensions_config.json"

    runtime_root.mkdir(parents=True, exist_ok=True)
    deer_flow_home.mkdir(parents=True, exist_ok=True)

    config_path.write_text(_render_config(profile, deer_flow_home, runtime_models), encoding="utf-8")
    if not extensions_config_path.exists():
        extensions_config_path.write_text(
            json.dumps({"mcpServers": {}, "skills": {}}, indent=2),
            encoding="utf-8",
        )

    os.environ["DEER_FLOW_HOME"] = str(deer_flow_home)
    os.environ["DEER_FLOW_HOST_BASE_DIR"] = str(deer_flow_home)
    os.environ["DEER_FLOW_CONFIG_PATH"] = str(config_path)
    os.environ["DEER_FLOW_EXTENSIONS_CONFIG_PATH"] = str(extensions_config_path)

    if not config_path.exists():
        raise RuntimeConfigError(f"Failed to materialize DeerFlow config bundle at {config_path}")

    logger.info(
        "Prepared DeerFlow runtime bundle: profile=%s instance=%s config=%s home=%s",
        profile.runtime_profile_id,
        DEFAULT_RUNTIME_INSTANCE_ID,
        config_path,
        deer_flow_home,
    )

    return RuntimeInstance(
        runtime_instance_id=DEFAULT_RUNTIME_INSTANCE_ID,
        runtime_profile_id=profile.runtime_profile_id,
        deployment_mode="local_process",
        config_path=config_path,
        deer_flow_home=deer_flow_home,
        extensions_config_path=extensions_config_path,
        health_status="ready",
    )
