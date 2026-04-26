# SwarmMind

> Open-source **Enterprise Agent Control Plane**.
> Turn fragmented internal systems into governed, auditable, agent-executable context.

[中文文档](README_zh.md)

## Why SwarmMind

Most "multi-agent" projects stop at collaboration demos. Enterprise deployment fails at the last mile:

- data is fragmented across OA/CRM/finance/HR/code systems;
- permissions are complex and high-risk;
- execution needs approval and rollback;
- leadership needs direct answers with evidence, not static reports.

SwarmMind focuses on this operational layer instead of chat-style agent orchestration.

## Product Positioning

SwarmMind is **not** just another multi-agent framework.

It is a control plane that provides:

- **Governed Context Layer**: provenance, permission scope, confidence, versioning, TTL, conflict sets;
- **Adaptive Routing & Policy Learning**: observable and reversible policy updates;
- **Execution Trace**: auditable steps, tool calls, evidence links, approval states;
- **Context-to-View Compiler**: compile context into typed views (status, timeline, risk, decision log).

## Core Principles

1. **AI agents are primary executors; humans are supervisors and referees.**
2. **State is context, not ticket fields.**
3. **Governance first**: permission boundaries and auditable execution are first-class.
4. **Enterprise-grade reliability** over demo-level autonomy.

## Documentation

- [Docs Home](docs/README.md)
- [Product Positioning](docs/product-positioning.md)
- [Technical Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [ChatSession Mainline Plan](docs/chat-mainline-execution-plan.md)
- [Archived v1 Narrative](docs/archive/README_v1_vision.md)

## Current Development Focus

- P0: keep ChatSession reliable and close `Promote to Project`
- P1: make Project execution governed with runs, artifacts, approvals, and audit
- P2: add enterprise connectors and policy intelligence after the main path works

## Quick Start

```bash
make install
make dev
```

## License

Apache-2.0
