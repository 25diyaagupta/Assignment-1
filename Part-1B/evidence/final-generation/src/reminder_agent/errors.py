"""Typed errors of the reminder agent (data-model.md §Errors, constitution X)."""


class ReminderAgentError(Exception):
    """Base class for every error the agent raises on purpose."""


class InvalidRequest(ReminderAgentError):
    """The request context is unusable (FR-003); no model call is made."""


class InvalidModelOutput(ReminderAgentError):
    """The model answered, but the reply cannot be used (counted as a wrong answer)."""


class ModelError(ReminderAgentError):
    """Base class for errors raised by the model client."""


class ModelTimeout(ModelError):
    """The model service did not answer within the configured timeout."""


class ModelRateLimited(ModelError):
    """The model service rejected the call because of rate limiting (HTTP 429)."""


class ModelUnavailable(ModelError):
    """The model service failed or could not be reached."""


class ModelConfigError(ModelError):
    """Missing key or a request the service rejects as misconfigured."""
