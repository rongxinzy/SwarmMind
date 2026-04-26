# Technical Architecture

## Architecture Goal

Provide a reliable control plane for enterprise agent execution with strict governance and full auditability.

## Logical Layers

1. **Connector Layer**
   - Ingests data and operations from enterprise systems (OA/CRM/finance/HR/code)
   - Normalizes source metadata and access scopes

2. **Governed Context Layer**
   - Stores structured context objects with:
     - provenance (`source`, `record_id`, `ingested_at`)
     - permission scope (`principal`, `resource`, `action`)
     - confidence score
     - version and TTL
     - conflict sets for contradictory facts

3. **Routing & Policy Layer**
   - Maps goals to specialized agents and tools
   - Learns from approvals/outcomes through reversible policy versions
   - Supports staged promotion of policies (draft/canary/active)

4. **Execution Layer**
   - Agent runtime and tool invocation
   - Policy checks for risky actions
   - Human approval gates where required

5. **Trace & Audit Layer**
   - Immutable event stream of execution steps
   - Links decisions to evidence and source context
   - Supports replay, inspection, and compliance export

6. **View Layer (Context-to-View Compiler)**
   - Compiles context into typed view schemas:
     - `StatusSummaryView`
     - `TimelineView`
     - `RiskMatrixView`
     - `DecisionLogView`
     - `EvidenceTableView`

## Core Design Rules

- **No blind writes**: all context mutations carry source and actor metadata
- **No implicit privilege escalation**: permission checks at every read/write/tool call
- **No silent policy drift**: policy updates are versioned, reviewable, and reversible
- **No unverifiable output**: user-facing conclusions should resolve to evidence references

## Human-in-the-loop Controls

- Approval policy by action category and risk level
- Bounded intervention API for supervisors
- Rollback hooks for critical write operations

## Reliability Considerations

- Idempotent connector ingestion
- Retry classification with deterministic side-effect boundaries
- Trace durability and retention policies
- Backpressure and timeout handling for long-running tasks
