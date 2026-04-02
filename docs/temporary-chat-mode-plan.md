# Temporary Chat Mode Plan

## Goal

This document defines the implementation plan for SwarmMind's temporary conversation flow launched from the sidebar `新建` entry.

Current scope is intentionally narrow:

- Focus on the temporary conversation entry flow only
- Support four explicit modes: `flash`, `thinking`, `pro`, `ultra`
- Reuse existing conversation persistence, streaming, and title generation
- Do not implement Project, Agent Team, or skill-center integration in this phase

## Product Definition

### Temporary Conversation

For this phase, a temporary conversation means:

- User enters the `新建` page without creating a persisted conversation immediately
- The UI stays in a draft state until the first message is sent
- A real conversation record is created only when the first message is submitted successfully
- After first send, the conversation behaves like a normal persisted thread

This follows the same high-level interaction pattern as deer-flow's `new -> first send -> real thread`, while staying compatible with SwarmMind's current single-page structure.

### Mode Semantics

SwarmMind will support these four modes as explicit runtime context:

- `flash`
  - Fast response
  - No reasoning
  - No plan mode
  - No subagents
- `thinking`
  - Reasoning enabled
  - No plan mode
  - No subagents
- `pro`
  - Reasoning enabled
  - Plan mode enabled
  - No subagents
- `ultra`
  - Reasoning enabled
  - Plan mode enabled
  - Subagents enabled

Mode must affect backend execution behavior, not just UI labels.

## Current State Summary

SwarmMind already has a usable baseline:

- Frontend has a chat surface, sidebar, conversation list, and recent conversations
- Backend already persists `conversations` and `messages`
- Streaming chat responses are implemented
- Conversation titles are generated after the first complete exchange
- The general-purpose path already routes into DeerFlow via `GeneralAgent`

Main gaps:

- Frontend currently sends only `reasoning: true/false`
- Frontend model selection is not actually submitted to the backend
- Backend has no first-class `mode` contract
- `GeneralAgent` behavior is still mostly fixed by constructor flags instead of per-request runtime config
- The `新建` page is not treated as a true temporary conversation draft state

## Implementation Principles

- Do not rebuild the app into deer-flow's full workspace architecture
- Keep SwarmMind's single-page structure for this phase
- Make `mode` an explicit first-class request field
- Centralize `mode -> runtime config` mapping in one backend helper
- Keep title generation timing unchanged
- Keep stream event protocol compatible unless strictly necessary
- Avoid Project or Team concepts in this first mode rollout

## Locked Decisions

These decisions are part of the implementation contract for this phase and should not be re-opened during normal development.

### Request Compatibility Rules

- `mode` is the primary control field for runtime behavior
- `reasoning` remains temporary backward compatibility only
- Resolution priority is:
  - if `mode` is present, ignore `reasoning`
  - if `mode` is absent, map `reasoning=True` to `thinking`
  - if `mode` is absent, map `reasoning=False` to `flash`
- `model_name` is optional in the request
- if `model_name` is missing or empty, backend falls back to the existing default model resolution path

### Temporary Conversation Persistence Rules

- Entering sidebar `新建` creates no database row
- Draft state exists only in frontend state for this phase
- First send flow remains:
  - call `POST /conversations`
  - if create succeeds, call `POST /conversations/{id}/messages/stream`
- A conversation is considered persisted as soon as `POST /conversations` succeeds
- If conversation creation succeeds but streaming fails, keep the conversation record
- If streaming fails after the user message is persisted, keep the partial conversation and surface the error in the chat UI
- Clicking sidebar `新建` always resets the current draft input, selected mode, runtime state, and selected persisted conversation
- Draft state is not preserved across view switches in this phase

### Runtime/Event Rules

- `flash`
  - must not emit `thinking`
  - must not emit DeerFlow-driven `team_task`
  - must not enable DeerFlow subagents
- `thinking`
  - may emit `thinking`
  - must not emit DeerFlow-driven `team_task`
  - must not enable DeerFlow subagents
- `pro`
  - may emit `thinking`
  - must not emit DeerFlow-driven `team_task`
  - must not enable DeerFlow subagents
- `ultra`
  - may emit `thinking`
  - may emit DeerFlow-driven `team_task`
  - may emit DeerFlow-driven `team_activity`
  - is the only mode allowed to enable DeerFlow subagents
- Existing non-DeerFlow specialized-agent activity events may remain as-is in this phase
- Therefore, the strict UI rule is:
  - `ultra` is the only mode that may surface collaborative DeerFlow task/activity cards
  - specialized single-agent execution events outside DeerFlow are not treated as the same product concept

### GeneralAgent Refactor Rules

- Do not create separate `GeneralAgent` subclasses per mode
- Keep one `GeneralAgent`
- Move runtime options from constructor-time assumptions to request-scoped parameters
- Preferred shape:
  - introduce a small runtime options object or typed dict
  - pass it into `act()` and `stream_events()`
- `GeneralAgent.__init__()` may still accept default fallbacks, but request-scoped options must override them

### Model Rules

- Frontend model picker values are the allowed `model_name` values for this phase
- Backend should accept any non-empty string `model_name` without introducing a new persistence table
- Backend should log and pass through `model_name` to DeerFlow config, not rewrite it
- Invalid or unsupported model names are handled by the underlying model/runtime layer, not by a new SwarmMind validation feature in this phase

## Implementation Checklist

### 1. Scope Freeze

- [ ] Keep this phase limited to the sidebar `新建` temporary conversation flow
- [ ] Do not introduce Project binding
- [ ] Do not introduce Agent Team management UI
- [ ] Do not introduce Skill Center integration
- [ ] Keep current conversation storage and title generation model

### 2. Backend Contract

- [ ] Add a `ConversationMode` enum in `swarmmind/models.py`
- [ ] Extend `SendMessageRequest` with:
  - [ ] `mode`
  - [ ] `model_name`
  - [ ] optional `reasoning_effort` only if needed later
- [ ] Keep the existing `reasoning` field temporarily for compatibility
- [ ] Add a single helper in `swarmmind/api/supervisor.py` to resolve runtime options from request payload

Expected mapping:

- [ ] `flash -> thinking_enabled=False, plan_mode=False, subagent_enabled=False`
- [ ] `thinking -> thinking_enabled=True, plan_mode=False, subagent_enabled=False`
- [ ] `pro -> thinking_enabled=True, plan_mode=True, subagent_enabled=False`
- [ ] `ultra -> thinking_enabled=True, plan_mode=True, subagent_enabled=True`

### 3. DeerFlow Runtime Integration

- [ ] Refactor `GeneralAgent` to accept per-request runtime options
- [ ] Ensure `act()` supports request-scoped runtime config
- [ ] Ensure `stream_events()` supports request-scoped runtime config
- [ ] Pass `model_name`, `thinking_enabled`, `plan_mode`, and `subagent_enabled` into DeerFlow runnable config
- [ ] Remove the current behavior where non-ultra requests may still use subagents by default

### 4. Conversation API Flow

- [ ] Keep `POST /conversations` as the creation endpoint
- [ ] Keep `POST /conversations/{id}/messages/stream` as the main streaming endpoint
- [ ] Update message streaming requests to accept `mode` and `model_name`
- [ ] Route all message execution paths through the same runtime option resolver
- [ ] Preserve existing stream event types:
  - [ ] `status`
  - [ ] `user_message`
  - [ ] `thinking`
  - [ ] `assistant_message`
  - [ ] `assistant_final`
  - [ ] `team_task`
  - [ ] `team_activity`
  - [ ] `title`
  - [ ] `done`

Behavior expectations:

- [ ] `flash` should not emit reasoning content
- [ ] `thinking` may emit reasoning content but should not create subagent task cards
- [ ] `pro` should behave like structured single-agent execution with planning enabled
- [ ] `ultra` is the only mode expected to clearly surface collaborative task/activity behavior

### 5. Frontend Temporary Conversation UX

- [ ] Keep sidebar `新建` as the entry point
- [ ] Treat entering `chat` view without a selected conversation as a draft temporary conversation state
- [ ] Do not create a conversation when entering the page
- [ ] Create the conversation only on first submit
- [ ] After first submit, switch the current chat into normal persisted mode

### 6. Frontend Composer and Mode Selector

- [ ] Add a mode selector to the chat composer in `ui/src/components/ui/v0-ai-chat.tsx`
- [ ] Add short descriptions for:
  - [ ] `flash`
  - [ ] `thinking`
  - [ ] `pro`
  - [ ] `ultra`
- [ ] Default mode to `pro`
- [ ] Keep mode changes local until send
- [ ] Do not clear the text input when switching modes
- [ ] Make model selection real by including the selected model in the request payload

### 7. Frontend Request Flow

- [ ] When no conversation exists yet:
  - [ ] First create conversation
  - [ ] Then send the message stream request
- [ ] When a conversation already exists:
  - [ ] Reuse the existing conversation ID
- [ ] Include `content`, `mode`, and `model_name` in the stream request
- [ ] Keep optimistic user message rendering
- [ ] Keep current stream event handling compatible

### 8. Empty-State and New-Chat Presentation

- [ ] Update the empty state to reflect temporary conversation positioning
- [ ] Make the page explain that this is the quick entry for exploration and one-off generation
- [ ] Keep quick prompts, but make them compatible with the new mode-driven flow
- [ ] Ensure the new-chat state is visually distinct from an existing conversation replay state

### 9. Persistence and Existing Conversation Compatibility

- [ ] Keep existing `conversations` and `messages` tables unchanged unless runtime metadata becomes necessary
- [ ] Preserve the current title generation timing
- [ ] Preserve recent conversation ordering by `updated_at`
- [ ] Preserve loading of existing messages when selecting a past conversation

### 10. Testing

- [ ] Add backend tests for `mode -> runtime config` mapping
- [ ] Add backend tests for old `reasoning` compatibility
- [ ] Extend streaming tests to cover mode-specific behavior
- [ ] Verify `flash` suppresses reasoning
- [ ] Verify `thinking` allows reasoning without subagent task cards
- [ ] Verify `ultra` can surface `team_task` and `team_activity`
- [ ] Keep title generation tests passing
- [ ] Manually verify frontend behavior:
  - [ ] Enter new chat
  - [ ] Change mode before first send
  - [ ] First send creates conversation
  - [ ] Recent conversations update
  - [ ] Existing conversation can be reopened

## File-Level Execution Plan

### Backend

#### `swarmmind/models.py`

- [ ] Add `ConversationMode` enum with:
  - [ ] `flash`
  - [ ] `thinking`
  - [ ] `pro`
  - [ ] `ultra`
- [ ] Extend `SendMessageRequest`:
  - [ ] `mode: ConversationMode | None = None`
  - [ ] `model_name: str | None = None`
  - [ ] keep `reasoning: bool = False`
- [ ] Do not change response models in this phase

#### `swarmmind/api/supervisor.py`

- [ ] Add a small runtime resolver near the conversation helpers:
  - [ ] normalize request payload into an effective mode
  - [ ] return `mode`, `model_name`, `thinking_enabled`, `plan_mode`, `subagent_enabled`
- [ ] Update `send_message()` to use the resolver instead of reading `body.reasoning` directly
- [ ] Update `_stream_conversation_message()` to use the resolver instead of reading `body.reasoning` directly
- [ ] Keep both sync and stream endpoints behaviorally aligned through the same helper
- [ ] Ensure `GeneralAgent` construction/invocation no longer hardcodes `subagent_enabled=True` for all requests
- [ ] Keep title generation path unchanged
- [ ] Keep persistence helpers unchanged unless needed for request plumbing only

#### `swarmmind/agents/general_agent.py`

- [ ] Introduce request-scoped runtime options support
- [ ] Update `act()` signature to accept runtime options
- [ ] Update `stream_events()` signature to accept runtime options
- [ ] Update `_run_deerflow_turn()` to pass runtime options through
- [ ] Build DeerFlow runnable config from:
  - [ ] effective `model_name`
  - [ ] effective `thinking_enabled`
  - [ ] effective `subagent_enabled`
  - [ ] `plan_mode` if supported through runnable config/context
- [ ] Ensure no subagent/task-card-producing path is enabled outside `ultra`

#### `tests/test_conversation_stream.py`

- [ ] Add resolver-focused tests for:
  - [ ] explicit `flash`
  - [ ] explicit `thinking`
  - [ ] explicit `pro`
  - [ ] explicit `ultra`
  - [ ] fallback `reasoning=True -> thinking`
  - [ ] fallback `reasoning=False -> flash`
- [ ] Add stream behavior assertions for:
  - [ ] no `thinking` in `flash`
  - [ ] no DeerFlow collaborative task cards in `thinking`
  - [ ] no DeerFlow collaborative task cards in `pro`

#### `tests/test_conversation_titles.py`

- [ ] Keep title generation tests unchanged unless request payload construction needs the new fields
- [ ] If needed, update test request builders to include explicit `mode=None`

### Frontend

#### `ui/src/App.tsx`

- [ ] Keep `activeConversationId` as the source of truth for persisted conversation selection
- [ ] Ensure `handleStartChat()` fully resets into draft temporary state
- [ ] Do not introduce a separate route for draft chat in this phase

#### `ui/src/components/ui/sidebar.tsx`

- [ ] Keep sidebar `新建` behavior as a simple entry into chat draft state
- [ ] Treat top-right plus button and `新建` nav item identically
- [ ] Do not add mode or project controls into the sidebar in this phase

#### `ui/src/components/ui/v0-ai-chat.tsx`

- [ ] Add a `ConversationMode` frontend type matching backend enum values
- [ ] Add local draft state for:
  - [ ] selected mode
  - [ ] selected model
- [ ] Default selected mode to `pro`
- [ ] Keep selected model default as current existing default
- [ ] Add mode selector UI beside or near the composer controls
- [ ] Update empty-state copy to reflect temporary conversation entry semantics
- [ ] Update `streamConversation()` request body to send:
  - [ ] `content`
  - [ ] `mode`
  - [ ] `model_name`
- [ ] Keep optimistic user message insertion
- [ ] Keep current JSON-line stream parsing
- [ ] Preserve message replay behavior when `conversationId` exists
- [ ] On `conversationId` becoming `undefined`, reset chat to draft temporary state
- [ ] On explicit new-chat entry, clear input and runtime state

## Developer Notes

- Implementation should begin from backend contract and resolver, not from UI polish
- Do not widen scope into persistent per-conversation mode metadata unless a real blocker appears
- If DeerFlow plan-mode wiring turns out to require a different field name, keep the SwarmMind resolver contract stable and adapt only inside `GeneralAgent`

## Implementation Order

Recommended order:

1. Define backend request contract and mode mapping
2. Refactor `GeneralAgent` runtime configuration path
3. Update streaming endpoint to consume the new mode contract
4. Update frontend temporary conversation state and composer
5. Add tests and run full regression

## Risks

### Known Technical Risks

- Frontend currently has model state that is not wired to the backend
- Backend currently uses a narrow `reasoning` boolean that collapses too many behaviors into one flag
- `GeneralAgent` currently initializes DeerFlow with constructor-time flags instead of request-time runtime flags
- New-chat draft state and existing conversation state are currently mixed inside one component

### Scope Risks

- Expanding this phase into Project or Team concepts will slow down delivery and blur acceptance criteria
- Adding too many advanced controls up front will weaken the value of the four-mode contract

## Acceptance Criteria

This work is complete when:

- Sidebar `新建` opens a real temporary conversation draft state
- No conversation is persisted until the first message is sent
- All four modes are visible and selectable in the UI
- The selected mode is transmitted to the backend
- Backend execution behavior changes according to mode
- Existing conversation replay, recent list behavior, and title generation do not regress

## Deferred Work

Not included in this phase:

- Project-scoped conversation promotion
- Team-scoped runtime governance
- Skill Center orchestration
- Cross-conversation mode memory
- Separate settings pages for advanced reasoning effort controls
