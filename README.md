<!-- Hero Tagline + Language Switcher -->
<p align="center">
  <h1>🤖 SwarmMind</h1>
  <strong>Where intelligent work emerges from collaboration.</strong><br>
  <em>AI agent teams as primary actors — humans as referees.</em>
  <br><br>
  <a href="README_zh.md">🇨🇳 中文版</a>
</p>

<!-- Badges -->
<p align="center">

  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/License-Apache--2.0-green.svg?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/Phase-1-orange.svg?style=flat-square" alt="Phase">
  <img src="https://img.shields.io/badge/AI%20Native-OS-black.svg?style=flat-square" alt="AI Native OS">
  <img src="https://img.shields.io/badge/Architecture-Context%20Broker-purple.svg?style=flat-square" alt="Architecture">

</p>

---

## The Problem

Every tool we build asks: *how do we help humans do knowledge work better?*

But we've never seriously asked:

> **What happens when knowledge work no longer requires humans at all?**

Not "AI assists humans." **AI agents become the primary actors.** Humans become supervisors and decision-makers — not bystanders, but referees.

SwarmMind is the answer.

---

## Old Paradigm → New Paradigm

| Tool | Old Paradigm (humans do, AI helps a little) | New Paradigm (AI agents do, humans supervise) |
|------|---------------------------------------------|---------------------------------------------|
| **Project Management** | Jira — humans create tickets, assign tasks | SwarmMind — AI routes goals, fills context gaps |
| **Knowledge Base** | Confluence — humans write & search docs | AI agents share context, LLM generates views |
| **Communication** | Slack — humans send, wait, reply | Agents write to shared context, no inbox |
| **Code Review** | GitHub PR — humans review manually | AI agents review, collaborate, self-improve |

**The shift:** *"humans are the main actors, AI is the assistant"* → ***AI agent teams are the main actors, humans are the referees.***

---

## What is SwarmMind

SwarmMind is an **operating system for AI agent teams** — not a message queue, not a workflow engine, not another "AI assistant." It's **enterprise cognitive infrastructure**.

The core OS insight: **multiple independent entities don't need to know each other exist to collaborate** — they just share resources, and the OS coordinates access.

```
┌─────────────────────────────────────────────────────────────┐
│                     You (human supervisor)                  │
│              "What's the status of this project?"           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               LLM STATUS RENDERER                           │
│     ┌───────────────────────────────────────────────────┐   │
│     │  On-demand: prose? table? Gantt? — LLM decides  │   │
│     └───────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │ reads accumulated context
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    CONTEXT BROKER                           │
│     Routes goals → right agent, manages shared state        │
└──────┬──────────┬──────────┬──────────┬───────────────────┘
       │          │          │          │
       ▼          ▼          ▼          ▼
   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
   │Finance │ │Customer│ │  Code │ │Product │
   │ Agent  │ │ Agent  │ │Review  │ │  Data  │
   └────────┘ └────────┘ └────────┘ └────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │   SHARED CONTEXT      │
        │  (all agents read &   │
        │   write one memory)   │
        └──────────────────────┘
```

**Why not message passing?** Imagine two human experts in the same room — they don't email each other, they share a whiteboard. SwarmMind is that shared room for AI agents.

---

## State is Context, Not Jira

Jira: `ticket.status = "In Progress"` → rigid, schema-enforced, forces work into 4 states.

**Real work never follows a 4-state flow.** A design iteration is simultaneously "draft," "in review," "waiting on client," and "partially done" — but Jira forces you to pick one.

### SwarmMind's answer:

> **State is not data. State is context.**

When you give an agent "write the quarterly financial report," the agent needs:
- **What's already there?** → existing context
- **What's missing?** → context gap detection
- **Who fills the gap?** → routes to the right agent

When all gaps are filled, the report writes itself. **No "In Progress," no tickets, no sub-tasks.**

Human asks "what's the status?" → LLM reads shared context → generates the best view (table, Gantt, or prose), **dynamically chosen by the LLM**.

---

## Self-Evolution: The Team Gets Smarter

Every existing AI system starts fresh every conversation. SwarmMind fixes this with **strategy tables**:

```
 Situation                  Routed to        Success Rate
────────────────────────────────────────────────────────────
"Quarterly financial R."   → Finance Agent      92%
"Python code review"       → Code Agent         87%
"Customer complaint"       → CS Agent           71%  ← needs improvement
"Competitive analysis"     → ???                0%  ← new situation
```

The system observes: which situation → which agent → approved or rejected → achieved goal?

Based on these signals, the system **automatically updates routing strategy** — supervised by humans, instantly effective, fully auditable.

**Not fine-tuning. Rule-based, observable, reversible learning.**

---

## Why Open Source

Because this is **infrastructure for your enterprise's brain**. No one entrusts a black box with their cognitive infrastructure.

The open source community will contribute: new agent types, better routing algorithms, novel collaboration patterns.

**Geek spirit:** making AI agent teams truly collaborate, self-evolve, and exhibit emergent intelligence. This isn't "another SaaS tool." It's rethinking the nature of knowledge work from first principles.

---

## Phase 1 Goals

> *"An AI agent team that collaborates on knowledge work, learns from every task, and answers 'how's the project going?' with an AI-generated real-time summary — not a Jira table."*

| # | Component | Description |
|---|-----------|-------------|
| 1 | **Two Specialized Agents** | Finance Q&A agent + Code review agent |
| 2 | **Shared Context Layer** | All agents read/write one memory |
| 3 | **Context Broker** | Routes goals to the right agent |
| 4 | **LLM Status Renderer** | On-demand status summaries (prose/table/Gantt) |
| 5 | **Human Supervisor Interface** | Observe, approve, or reject every action |
| 6 | **Strategy Table** | Records routing rules, tracks success rate |

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/rongxinzy/SwarmMind.git
cd SwarmMind

# Backend: install dependencies
pip install -r requirements.txt

# Start the supervisor API (auto-inits DB on first run)
python -m swarmmind.api.supervisor
# API runs at http://localhost:8000

# Frontend: install UI dependencies (new terminal)
cd ui && npm install && npm run dev
# UI runs at http://localhost:3000
```

**Workflow:** Open the UI at http://localhost:3000 → submit a goal → approve/reject proposals in the Pending tab.

---

## Architecture

| Layer | Component | Responsibility |
|-------|------------|-----------------|
| **Human Interface** | Supervisor UI (shadcn/ui) + LLM Status Renderer | Submit goals, approve/reject, view status |
| **Orchestration** | Context Broker | Routes goals to agents via strategy table |
| **Agent Layer** | Finance Agent, Code Review Agent | Specialized domain actors with LLM inference |
| **Memory Layer** | Shared Context (SQLite KV) | Persistent shared memory, conflict-resolved |
| **Supervisor API** | FastAPI REST API | Human oversight and approval endpoints |

---

## Project Status

🟡 **Phase 1 — Core Complete**

Building the minimal working system:
- [x] Project concept & design
- [x] Context Broker implementation
- [x] Finance + Code Review agents
- [x] Shared context layer (SQLite KV)
- [x] Supervisor REST API (6 endpoints + pagination)
- [x] Supervisor UI (React + shadcn/ui, 3 tabs)
- [x] LLM Status Renderer
- [x] Strategy table with success tracking
- [x] Action proposal timeout (5 min)
- [x] Core tests

---

## Contributing

Contributions welcome. This is an open experiment in AI-native infrastructure.

- Fork the repo
- Read the [design doc](./docs/design.md) for architecture context
- Open an issue before submitting large PRs

---

## License

Apache 2.0 — see [LICENSE](LICENSE)

---

<p align="center">

🇨🇳 <a href="README_zh.md">中文版</a>

*SwarmMind — where intelligent work emerges from collaboration.*

</p>
