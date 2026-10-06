class CertificateGenerationError(RuntimeError):
    """Raised when a certificate cannot be generated for a recipient."""


class StorageValidationError(ValueError):
    """Raised when a resolved file path escapes the configured storage directory."""


class JobNotFoundError(RuntimeError):
    """Raised when a requested job cannot be found."""


class CertificateNotFoundError(RuntimeError):
    """Raised when a requested certificate cannot be found."""
