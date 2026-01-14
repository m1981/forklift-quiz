import logging
import time
import uuid
import sys
from contextvars import ContextVar
from functools import wraps
from typing import Optional, Dict, Any

# --- Prometheus Imports ---
from prometheus_client import Histogram, REGISTRY

# --- Context for Correlation IDs ---
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="system")

# --- Prometheus Metric Definition ---
METRIC_NAME = 'app_method_duration_seconds'
try:
    METHOD_DURATION = Histogram(METRIC_NAME, 'Time spent in method', ['component', 'method'])
except ValueError:
    METHOD_DURATION = REGISTRY._names_to_collectors[METRIC_NAME]


def measure_time(metric_name: str):
    """Decorator for timing methods + logging."""

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            start = time.perf_counter()
            component = self.__class__.__name__
            method = func.__name__

            try:
                result = func(self, *args, **kwargs)
                duration = time.perf_counter() - start

                # Prometheus
                METHOD_DURATION.labels(component=component, method=method).observe(duration)

                # Console Log
                telemetry = getattr(self, 'telemetry', None)
                if telemetry:
                    telemetry.log_info(f"⏱️ {metric_name}", duration_ms=round(duration * 1000, 2))

                return result
            except Exception as e:
                duration = time.perf_counter() - start
                METHOD_DURATION.labels(component=component, method=method).observe(duration)

                telemetry = getattr(self, 'telemetry', None)
                if telemetry:
                    telemetry.log_error(f"💥 Failed: {metric_name}", e, duration_ms=round(duration * 1000, 2))
                raise e

        return wrapper

    return decorator


class Telemetry:
    """
    Facade for Logs, Metrics, and Tracing.
    """

    def __init__(self, component_name: str):
        self.component = component_name
        self._setup_logger()

    def _setup_logger(self):
        """Initializes the logger. Safe to call multiple times."""
        self.logger = logging.getLogger(self.component)

        # Ensure we output to console if not configured
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def __getstate__(self):
        """Pickling: Save everything EXCEPT the logger."""
        state = self.__dict__.copy()
        if 'logger' in state:
            del state['logger']
        return state

    def __setstate__(self, state):
        """Unpickling: Restore state and re-create logger."""
        self.__dict__.update(state)
        self._setup_logger()

    @staticmethod
    def start_trace() -> str:
        c_id = str(uuid.uuid4())[:8]
        correlation_id_ctx.set(c_id)
        return c_id

    @staticmethod
    def get_trace_id() -> str:
        return correlation_id_ctx.get()

    def log_info(self, event: str, **kwargs):
        trace_id = self.get_trace_id()
        msg = f"[{trace_id}] {event} | {kwargs}"
        self.logger.info(msg)

    def log_error(self, event: str, error: Exception, **kwargs):
        trace_id = self.get_trace_id()
        msg = f"[{trace_id}] ❌ {event} | Error: {str(error)} | {kwargs}"
        self.logger.error(msg, exc_info=True)