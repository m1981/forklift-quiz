import logging
import time
import uuid
from contextvars import ContextVar
from functools import wraps
from typing import Optional, Dict, Any

# --- Prometheus Imports ---
from prometheus_client import Histogram, REGISTRY

# --- Context for Correlation IDs ---
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="system")

# --- Prometheus Metric Definition (Safe for Reloading) ---
METRIC_NAME = 'app_method_duration_seconds'

try:
    # Try to create the metric
    METHOD_DURATION = Histogram(
        METRIC_NAME,
        'Time spent in method',
        ['component', 'method']
    )
except ValueError:
    # If Streamlit reloads, the metric already exists in the Global Registry.
    # We must retrieve the existing instance to avoid the "Duplicated timeseries" error.
    # Note: Accessing _names_to_collectors is the standard workaround for this specific library issue.
    METHOD_DURATION = REGISTRY._names_to_collectors[METRIC_NAME]


def measure_time(metric_name: str):
    """
    Standalone decorator for timing methods.
    It records to Prometheus AND logs to standard logging.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            start = time.perf_counter()

            # 1. Prometheus Observation
            # We use the class name as 'component' and method name as 'method'
            component = self.__class__.__name__
            method = func.__name__

            try:
                result = func(self, *args, **kwargs)
                duration = (time.perf_counter() - start)  # Seconds for Prometheus

                # Record to Prometheus
                METHOD_DURATION.labels(component=component, method=method).observe(duration)

                # Record to Logs (ms)
                duration_ms = duration * 1000
                telemetry = getattr(self, 'telemetry', None)
                if telemetry:
                    telemetry.log_info(f"Metric: {metric_name}", duration_ms=round(duration_ms, 2))

                return result
            except Exception as e:
                duration = (time.perf_counter() - start)
                duration_ms = duration * 1000

                # Record to Prometheus (even on failure, time was spent)
                METHOD_DURATION.labels(component=component, method=method).observe(duration)

                telemetry = getattr(self, 'telemetry', None)
                if telemetry:
                    telemetry.log_error(f"Failed: {metric_name}", e, duration_ms=round(duration_ms, 2))
                raise e

        return wrapper

    return decorator


class Telemetry:
    """
    A facade for the Three Pillars: Logs, Metrics, Tracing.
    """

    def __init__(self, component_name: str):
        self.logger = logging.getLogger(component_name)
        self.component = component_name

    @staticmethod
    def start_trace() -> str:
        """Generates a new Correlation ID for a user interaction."""
        c_id = str(uuid.uuid4())[:8]
        correlation_id_ctx.set(c_id)
        return c_id

    @staticmethod
    def get_trace_id() -> str:
        return correlation_id_ctx.get()

    def log_info(self, event: str, **kwargs):
        """Structured Logging: Log events as data, not just strings."""
        payload = {
            "event": event,
            "trace_id": self.get_trace_id(),
            "component": self.component,
            **kwargs
        }
        self.logger.info(f"[{self.component}] {event} | {payload}")

    def log_error(self, event: str, error: Exception, **kwargs):
        payload = {
            "event": event,
            "trace_id": self.get_trace_id(),
            "error_type": type(error).__name__,
            "error_msg": str(error),
            **kwargs
        }
        self.logger.error(f"[{self.component}] ❌ {event} | {payload}", exc_info=True)