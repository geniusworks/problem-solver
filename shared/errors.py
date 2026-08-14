"""Error classes for the problem solver."""

class BaseError(Exception):
    """Base class for all custom exceptions."""
    pass

class ValidationError(BaseError):
    """Base class for validation-related errors."""
    pass

class SessionError(ValidationError):
    """Raised when there are issues with session management."""
    pass

class InputError(ValidationError):
    """Raised for errors related to input data."""
    pass

class SubmissionError(ValidationError):
    """Raised for errors during solution submission."""
    pass

class ProviderError(BaseError):
    """Base class for errors related to model providers."""
    pass

class RateLimitError(ProviderError):
    """Raised when a rate limit is exceeded."""
    pass

class ProviderTimeoutError(ProviderError):
    """Raised when a provider times out."""
    pass

class AuthenticationError(ProviderError):
    """Raised when authentication fails."""
    pass

class ServiceUnavailableError(ProviderError):
    """Raised when a service is unavailable."""
    pass

class ExecutionError(BaseError):
    """Base class for execution-related errors."""
    pass

class ResourceError(ExecutionError):
    """Raised when resource limits are exceeded."""
    pass

class CompilationError(ExecutionError):
    """Raised when code fails to compile."""
    pass

# Note: execution timeouts and runtime failures use Python's builtin
# TimeoutError / RuntimeError. Custom subclasses that shadowed those builtins
# once lived here; they were unused and have been removed to avoid the shadow.
