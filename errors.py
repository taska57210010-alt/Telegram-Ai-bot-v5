"""
Custom exceptions and error utilities.
"""


class BotError(Exception):
    """Base exception for bot errors."""

    pass


class InsufficientBalanceError(BotError):
    """Raised when user doesn't have enough questions."""

    pass


class InvalidModelError(BotError):
    """Raised when user selects invalid model."""

    pass


class PaymentError(BotError):
    """Raised when payment processing fails."""

    pass


class DatabaseError(BotError):
    """Raised when database operation fails."""

    pass


class APIError(BotError):
    """Raised when external API call fails."""

    pass


def is_client_error(code: int) -> bool:
    """Check if HTTP status code is client error (4xx)."""
    return 400 <= code < 500


def is_server_error(code: int) -> bool:
    """Check if HTTP status code is server error (5xx)."""
    return 500 <= code < 600


def is_retriable_error(code: int) -> bool:
    """Check if error is retriable."""
    return is_server_error(code) or code == 429  # Rate limit
