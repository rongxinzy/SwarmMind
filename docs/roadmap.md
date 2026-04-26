# Roadmap

> Document type: [A] target roadmap.
> Roadmap principle: prove one useful governed work path before building a broad enterprise platform.

## Prioritization Framework

- **P0: Main path reliability.** A user can start a `ChatSession`, understand execution state, recover from errors, and promote valuable work into a real `Project`.
- **P1: Project governance.** Formal work has runs, artifacts, approvals, audit, and minimal membership semantics.
- **P2: Enterprise scale.** Connectors, policy intelligence, runtime pools, and plugin governance expand only after the main path has repeatable value.

## Phase Plan

| Phase | Priority | Theme | Outcomes |
|---|---|---|---|
| Phase A | P0 | ChatSession + DeerFlow Gateway foundation | Reliable conversation lifecycle, stream-state visibility, runtime bootstrap, model catalog foundation, trace reconstruction baseline |
| Phase B | P0 | ChatSession to Project closure | Minimal Project model, Promote to Project, Project page with real data, trace summary, artifact/evidence handoff |
| Phase C | P1 | Governed Project execution | Project tasks, runs, artifacts, approvals, audit log, minimal project membership/RBAC, AgentTeamTemplate instantiation |
| Phase D | P2 | Enterprise scale | Priority connectors, policy evaluation/versioning, runtime pools, richer routing, private skill/plugin governance |

## Immediate Milestones

### M1. Keep ChatSession Dependable

Already implemented work should stay protected while new features land:

- stable create/switch/delete/recover conversation lifecycle;
- semantic stream events for thinking, running, artifact, clarification, error, and done states;
- model catalog and mode language that users can understand;
- regression tests for stream, title, runtime bridge, and catalog behavior.

### M2. Close Promote to Project

This is the next decisive product slice.

- Add a minimal `Project` table/repository/API surface.
- Add a `Promote to Project` endpoint from a completed or valuable `ChatSession`.
- Generate a structured project seed: title, goal, scope, constraints, source conversation, and next step.
- Render a Project page that uses real data instead of a placeholder.
- Keep the source ChatSession as provenance rather than copying it into the project.

### M3. Make Trace and Artifacts Useful

- Attach run identifiers and trace summaries to assistant outputs.
- Show readable execution summaries without exposing raw DeerFlow checkpoint structure.
- Persist minimal artifact/evidence records that can feed Project views.
- Define retry/resume behavior at the run level.

### M4. Add Governance Only Where Risk Is Real

- Introduce approval only for high-risk capability use.
- Anchor approvals on `project_id` and `run_id`.
- Persist approval decisions into audit history.
- Avoid proposal screens for ordinary low-risk actions.

## Deferred Until After M2/M3

These are valid but should not interrupt the current route:

- full login, organization management, and complete RBAC;
- provider CRUD and tenant-level model administration;
- broad implementation of Teams, Skills, Knowledge, Assets, and Schedules pages;
- connector marketplace or private plugin governance;
- runtime pool isolation beyond the default local/runtime profile path.

## Success Metrics

- Time from first prompt to useful assistant result.
- Percent of valuable sessions successfully promoted into Projects.
- Percent of Project pages showing real state rather than placeholder state.
- Trace completeness for completed runs.
- Recovery rate after stream/runtime failure.
- High-risk approval precision: approvals should catch meaningful risk without interrupting routine work.

## Current Product Bet

The near-term bet is not "build every enterprise-control-plane feature." It is:

**If SwarmMind can reliably turn exploratory conversation into governed project execution, then enterprise governance features have a concrete surface to attach to.**

Everything else should serve that bet.
