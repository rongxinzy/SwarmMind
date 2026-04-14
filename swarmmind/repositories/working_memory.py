"""Working memory repository compatibility wrapper."""

from __future__ import annotations

from swarmmind.shared_memory import SharedMemory


class WorkingMemoryRepository:
    """Compatibility wrapper over SharedMemory.

    Keep the repository API stable while routing all working-memory semantics
    through a single implementation source in ``SharedMemory``.
    """

    _READ_AGENT_ID = "working_memory_repository"

    def _shared_memory(self, agent_id: str | None = None) -> SharedMemory:
        return SharedMemory(agent_id or self._READ_AGENT_ID)

    def read(self, key: str) -> dict | None:
        """Read a key from working memory. Returns None if not found."""
        return self._shared_memory().read(key)

    def write(
        self,
        key: str,
        value: str,
        domain_tags: str | None,
        agent_id: str,
    ) -> None:
        """Write a key to working memory."""
        self._shared_memory(agent_id).write(key, value, domain_tags)

    def read_all_by_tag(self, domain_tag: str) -> list[dict]:
        """Read all entries matching a domain tag."""
        return self._shared_memory().read_all_by_tag(domain_tag)

    def read_all(self) -> list[dict]:
        """Read all entries in working memory."""
        return self._shared_memory().read_all()
