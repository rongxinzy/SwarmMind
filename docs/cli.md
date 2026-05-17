# SwarmMind CLI

The `swarmmind` command is a first-class, HTTP-first client for the FastAPI supervisor API. It does not run service-layer business logic in-process; all execution still happens through the API boundary.

## Install And Configure

```bash
uv sync
swarmmind --help
```

API URL resolution order:

1. `--api-url`
2. `SWARMMIND_API_URL`
3. `http://127.0.0.1:8000`

Useful startup loop:

```bash
swarmmind serve --host 127.0.0.1 --port 8000
swarmmind health
swarmmind ready --json
```

## Output Modes

All commands default to human-readable output. Add `--json` for machine-readable JSON.

Streaming commands emit NDJSON in `--json` mode, one event per line:

```bash
swarmmind --json chat stream <conversation_id> "plan the CRM MVP"
```

Exit codes:

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | API or runtime error |
| `2` | CLI argument or contract validation error |
| `3` | Backend unavailable or timed out |
| `4` | Resource not found |

## Command Surface

System:

```bash
swarmmind health
swarmmind ready
swarmmind serve --host 127.0.0.1 --port 8000
```

Conversation and chat:

```bash
swarmmind conversation list
swarmmind conversation create --title "CRM discovery"
swarmmind conversation get <conversation_id> --include-messages
swarmmind conversation messages <conversation_id>
swarmmind conversation trace <conversation_id>
swarmmind conversation export <conversation_id> --format markdown
swarmmind conversation delete <conversation_id>

swarmmind chat send <conversation_id> "hello"
swarmmind chat stream <conversation_id> "build the plan" --mode pro
swarmmind chat new "start a governed CRM discovery" --mode ultra
swarmmind chat respond-clarification <conversation_id> <tool_call_id> "answer"
```

Governance:

```bash
swarmmind project list --limit 20
swarmmind project create "CRM MVP" --goal "Validate enterprise wedge"
swarmmind project update <project_id> --phase "planning" --risk-level medium
swarmmind project overview <project_id>
swarmmind project stream <project_id> "run the next step" --mode pro

swarmmind run list --project-id <project_id>
swarmmind run get <run_id>
swarmmind run create --project-id <project_id> --goal "execute plan"
swarmmind run update <run_id> --status completed --summary "done"

swarmmind task list <project_id>
swarmmind task create <project_id> "Write PRD" --priority high
swarmmind task update <project_id> <task_id> --status in_progress
swarmmind task delete <project_id> <task_id>

swarmmind approval list --project-id <project_id>
swarmmind approval create <project_id> "Approve CRM write" --risk-tier high
swarmmind approval update <approval_id> --status approved --decision-reason "approved"

swarmmind audit list --project-id <project_id>
swarmmind audit get <audit_id>
```

Dispatch and memory:

```bash
swarmmind dispatch "route this goal"
swarmmind memory list --layer L3_project --scope-id <project_id>
swarmmind memory get decision --layer L3_project --scope-id <project_id>
```

MCP:

```bash
swarmmind mcp serve
```

The MCP server exposes health, dispatch, ChatSession creation/send, project list/create, and memory get tools over stdio.
