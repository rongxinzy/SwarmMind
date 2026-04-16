# Changelog

## [0.1.1.1] - 2026-04-16

### Added
- Added `tests/e2e/` directory with standalone E2E test scripts for backend conversation stream across flash, thinking, pro, and ultra modes.
- Added `run_e2e_qa.py` for full four-mode stream validation, event collection, and backend stability scanning.
- Added `run_ultra_only.py` for focused ultra-mode stream testing.
- Added `generate_reports.py` for report generation from collected E2E data.

### Changed
- Updated `.gitignore` to exclude `tests/e2e_outputs/` and local E2E task docs from version control.
- Updated `uv.lock` to reflect the current package version.

## [0.1.1.0] - 2026-04-16

### Added
- Added `/conversations/recent` endpoint to fetch the most recent active conversation (within 7 days) with its messages.
- Added `include_messages` query parameter to `/conversations/{id}` to optionally load messages inline.
- Added `run_id` tracking to messages for retry and trace correlation.
- Added `promoted_project_id` to conversations to support project promotion workflow.
- Added semantic stream event layer (`status.thinking`, `content.accumulated`, `status.running`, `status.artifact`, `status.clarification`, `task_started`, `task_completed`, `task_failed`) for richer UI feedback.
- Added URL sync and browser history support to the chat workspace: conversations are reflected in the URL and back/forward navigation works.
- Added recovery on app load: automatically restores the most recent conversation if no URL parameter is present.
- Added `next_conversation_id` to delete conversation response so the UI can gracefully switch to the next available conversation.
- Added new test coverage for conversation detail, recent conversation, restaurant agent team snapshots, and runtime model catalog options.

### Changed
- Refactored runtime bridge to use a shared global event loop when the caller already has an active loop, preventing "Event loop is closed" errors from cached async primitives.
- Improved stream error handling: client disconnections are detected and logged cleanly without surfacing as runtime errors.
- Updated chat UI components (`v0-ai-chat`, `chat-composer-panel`, `chat-message-area`, `chat-empty-state`, `chat-message-ui`) to consume the new semantic stream events and support mode-based rendering.
- Updated sidebar to show recent-conversation loading state.

### Fixed
- Fixed SQLite foreign-key cascade behavior by explicitly deleting messages before deleting a conversation.
- Fixed timeout error classification in conversation stream to emit a dedicated `TIMEOUT` error code.
