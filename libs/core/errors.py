"""Custom exceptions for Tracker system."""

class TrackerError(Exception):
    """Base exception for all Tracker errors."""
    pass

class EnrollmentError(TrackerError):
    """Raised when device enrollment fails."""
    pass

class AuthenticationError(TrackerError):
    """Raised when authentication fails."""
    pass

class ConfigurationError(TrackerError):
    """Raised when configuration is invalid."""
    pass

class NetworkError(TrackerError):
    """Raised when network operations fail."""
    pass

class StorageError(TrackerError):
    """Raised when storage operations fail."""
    pass

class CommandExecutionError(TrackerError):
    """Raised when command execution fails."""
    pass

class SecurityError(TrackerError):
    """Raised when security checks fail."""
    pass

class ValidationError(TrackerError):
    """Raised when data validation fails."""
    pass
