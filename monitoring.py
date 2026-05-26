"""
Production monitoring with Sentry and Prometheus.
Essential for operating at 100K+ user scale.
"""

import logging
import time
from functools import wraps
from typing import Optional

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from prometheus_client import (
    Counter, Histogram, Gauge, start_http_server, REGISTRY
)

from config import config

logger = logging.getLogger(__name__)


# ============ Prometheus Metrics ============

# Request metrics
requests_total = Counter(
    'telegram_bot_requests_total',
    'Total requests',
    ['type', 'status']
)

# Question metrics
questions_asked_total = Counter(
    'questions_asked_total',
    'Total questions asked',
    ['model', 'status']
)

questions_duration_seconds = Histogram(
    'questions_duration_seconds',
    'Question processing duration',
    ['model']
)

# Payment metrics
payments_total = Counter(
    'payments_total',
    'Total payments',
    ['status']
)

payments_amount_stars = Counter(
    'payments_amount_stars_total',
    'Total stars received'
)

# User metrics
active_users = Gauge(
    'active_users',
    'Number of active users'
)

user_balance_total = Gauge(
    'user_balance_total',
    'Total user question balance'
)

# System metrics
database_connections = Gauge(
    'database_connections',
    'Active database connections'
)

cache_hits = Counter(
    'cache_hits_total',
    'Cache hits'
)

cache_misses = Counter(
    'cache_misses_total',
    'Cache misses'
)

# Error metrics
errors_total = Counter(
    'errors_total',
    'Total errors',
    ['type']
)

# Rate limit metrics
rate_limit_exceeded = Counter(
    'rate_limit_exceeded_total',
    'Rate limit exceeded',
    ['type']
)


# ============ Monitoring Manager ============

class MonitoringManager:
    """Centralized monitoring manager."""

    def __init__(self):
        """Initialize monitoring."""
        self.sentry_initialized = False
        self.prometheus_initialized = False

    def initialize(self) -> None:
        """Initialize monitoring services."""
        # Initialize Sentry
        if config.SENTRY_DSN:
            try:
                sentry_sdk.init(
                    dsn=config.SENTRY_DSN,
                    environment=config.SENTRY_ENVIRONMENT,
                    traces_sample_rate=config.SENTRY_TRACES_SAMPLE_RATE,
                    integrations=[
                        LoggingIntegration(
                            level=logging.INFO,
                            event_level=logging.ERROR
                        )
                    ],
                    before_send=self._before_send_sentry,
                )
                self.sentry_initialized = True
                logger.info("✅ Sentry monitoring initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Sentry: {e}")

        # Initialize Prometheus
        if config.PROMETHEUS_ENABLED:
            try:
                start_http_server(config.PROMETHEUS_PORT)
                self.prometheus_initialized = True
                logger.info(f"✅ Prometheus metrics server started on port {config.PROMETHEUS_PORT}")
            except Exception as e:
                logger.warning(f"Failed to start Prometheus server: {e}")

    def _before_send_sentry(self, event, hint):
        """Filter Sentry events before sending."""
        # Filter by exception type, not string content (to avoid false positives)
        if "exc_info" in hint:
            exc_type, _, _ = hint["exc_info"]
            # Don't send rate limit errors to Sentry (expected behavior)
            if exc_type.__name__ in ("TelegramRetryAfter", "RateLimitError"):
                return None
        return event

    def capture_exception(self, error: Exception, context: Optional[dict] = None):
        """Capture exception to Sentry."""
        if self.sentry_initialized:
            with sentry_sdk.push_scope() as scope:
                if context:
                    for key, value in context.items():
                        scope.set_context(key, value)
                sentry_sdk.capture_exception(error)

    def capture_message(self, message: str, level: str = "info"):
        """Capture message to Sentry."""
        if self.sentry_initialized:
            sentry_sdk.capture_message(message, level=level)


# Global monitoring instance
monitoring = MonitoringManager()


# ============ Decorators ============

def track_time(metric_name: str, labels: Optional[dict] = None):
    """Decorator to track function execution time."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Record metric
                if labels:
                    questions_duration_seconds.labels(**labels).observe(duration)
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                errors_total.labels(type=type(e).__name__).inc()
                raise
        
        return wrapper
    return decorator


def count_requests(request_type: str):
    """Decorator to count requests."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                requests_total.labels(type=request_type, status='success').inc()
                return result
            except Exception as e:
                requests_total.labels(type=request_type, status='error').inc()
                raise
        
        return wrapper
    return decorator
