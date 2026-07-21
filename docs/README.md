# SwarmMind Documentation

This directory contains product, architecture, roadmap, and implementation-planning documents for SwarmMind.

## Document Classes

SwarmMind uses two document classes:

- **[A] Target architecture/product documents** describe what the product should become. They guide future implementation and should be changed only when the product or architecture decision changes.
- **[B] Implementation status/planning documents** describe what is currently implemented or what one execution slice plans to do. They should not redefine the target architecture.

## Structure

- `product-positioning.md` [A]: one-line positioning, the four product surfaces (Chat / 任务 / Project / 组织管理), and product boundaries.
- `architecture.md` [A]: architecture baseline, terminology, execution paths, control-plane store boundaries, organization/permission model, and non-goals.
- `roadmap.md` [A]: milestone roadmap (M0-M4) and immediate priorities.
- `agent-action-roadmap.md` [B]: agent-facing execution guide that translates target docs into implementation order.
- `ui/` [A]: page maps, flows, and interaction rules.
- `cli.md` [B]: CLI command reference.
- `research/` [B]: dated research notes.

`AGENTS.md` at the repository root is the current engineering-status entry point. It maps code implementation to the target architecture.

Superseded documents are deleted outright — git history is the archive.

## Reading Order

For product and architecture decisions:

1. `product-positioning.md`
2. `architecture.md`
3. `roadmap.md`
4. `ui/`

For implementation work:

1. `AGENTS.md`
2. `architecture.md`
3. `roadmap.md`
4. `agent-action-roadmap.md`
5. the relevant `docs/ui/*` file

## Governance Rules

- `architecture.md` is the architecture baseline.
- `roadmap.md` decides milestone ordering.
- If code proves the architecture wrong, update `architecture.md` through an explicit architecture decision instead of silently letting implementation redefine the target.
- When a document becomes outdated, delete it; do not keep an `archive/` directory.
