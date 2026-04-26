# SwarmMind Documentation

This directory contains product, architecture, roadmap, and implementation-planning documents for SwarmMind.

## Document Classes

SwarmMind uses two document classes:

- **[A] Target architecture/product documents** describe what the product should become. They guide future implementation and should be changed only when the product or architecture decision changes.
- **[B] Implementation status/planning documents** describe what is currently implemented or what one execution slice plans to do. They should not redefine the target architecture.

## Structure

- `product-positioning.md` [A]: ICP, problem framing, product boundaries, differentiation, and current wedge.
- `architecture.md` [A]: architecture baseline, terminology, control-plane/runtime boundary, store boundaries, and phase architecture.
- `roadmap.md` [A]: pragmatic phase roadmap and immediate milestones.
- `agent-action-roadmap.md` [B]: agent-facing execution guide that translates target docs into implementation order.
- `ui/` [A]: page maps, flows, and interaction rules.
- `enterprise-crm-user-story.md` [A]: scenario validation for the target architecture.
- `chat-mainline-execution-plan.md` [B]: current ChatSession-first execution plan.
- `technical-debt-repayment-plan.md` [B]: current technical debt posture.
- `sprint-*` [B]: dated sprint plans and PRDs.
- `archive/` [B]: historical or superseded context.

`AGENTS.md` at the repository root is the current engineering-status entry point. It maps code implementation to the target architecture.

## Reading Order

For product and architecture decisions:

1. `product-positioning.md`
2. `architecture.md`
3. `roadmap.md`
4. `enterprise-crm-user-story.md`
5. `ui/`

For implementation work:

1. `AGENTS.md`
2. `architecture.md`
3. `roadmap.md`
4. `agent-action-roadmap.md`
5. `chat-mainline-execution-plan.md`
6. the relevant `docs/sprint-*` or `docs/ui/*` file

## Governance Rules

- `architecture.md` is the architecture baseline.
- `roadmap.md` decides phase ordering; sprint plans should not quietly reorder the product.
- Dated sprint documents may become stale and should be treated as execution snapshots.
- If code proves the architecture wrong, update `architecture.md` through an explicit architecture decision instead of silently letting implementation redefine the target.
