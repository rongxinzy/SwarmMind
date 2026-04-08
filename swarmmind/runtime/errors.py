"""Typed runtime errors for DeerFlow runtime lifecycle."""


class RuntimeErrorBase(Exception):
    """Base class for DeerFlow runtime errors."""

    code = "runtime_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class RuntimeConfigError(RuntimeErrorBase):
    """Raised when runtime configuration cannot be prepared."""

    code = "runtime_config_invalid"


class RuntimeUnavailableError(RuntimeErrorBase):
    """Raised when a runtime instance cannot be provisioned or used."""

    code = "runtime_unavailable"


class RuntimeExecutionError(RuntimeErrorBase):
    """Raised when DeerFlow execution fails after runtime bootstrap."""

    code = "runtime_execution_failed"
