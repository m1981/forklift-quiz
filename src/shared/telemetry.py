import logging
import sys
import time
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from functools import wraps
from typing import Any, ParamSpec, TypeVar, cast

# --- Prometheus Imports ---
from prometheus_client import REGISTRY, Histogram

# --- Context for Correlation IDs ---
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="system")

# --- Prometheus Metric Definition ---
METRIC_NAME = "app_method_duration_seconds"

# Explicitly declare the type for module-level usage
METHOD_DURATION: Histogram

try:
    METHOD_DURATION = Histogram(
        METRIC_NAME, "Time spent in method", ["component", "method"]
    )
except ValueError:
    # If it already exists, we get it from the registry.
    # We cast it to Histogram to satisfy Mypy.
    _collector = REGISTRY._names_to_collectors[METRIC_NAME]
    METHOD_DURATION = cast(Histogram, _collector)

# --- Type Definitions for Decorator ---
P = ParamSpec("P")
R = TypeVar("R")


def measure_time(metric_name: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator for timing methods + logging.
    Uses ParamSpec to preserve the signature of the decorated function.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start = time.perf_counter()

            # We assume this decorator is used on instance methods where
            # args[0] is 'self'. We use 'Any' for self extraction to avoid
            # complex protocol definitions.
            self_obj: Any = args[0] if args else None

            component = self_obj.__class__.__name__ if self_obj else "Unknown"
            method = func.__name__

            try:
                result = func(*args, **kwargs)
                duration = time.perf_counter() - start

                # Prometheus
                METHOD_DURATION.labels(component=component, method=method).observe(
                    duration
                )

                # Console Log
                telemetry = getattr(self_obj, "telemetry", None)
                if telemetry:
                    telemetry.log_info(
                        f"⏱️ {metric_name}", duration_ms=round(duration * 1000, 2)
                    )

                return result
            except Exception as e:
                duration = time.perf_counter() - start
                METHOD_DURATION.labels(component=component, method=method).observe(
                    duration
                )

                telemetry = getattr(self_obj, "telemetry", None)
                if telemetry:
                    telemetry.log_error(
                        f"💥 Failed: {metric_name}",
                        e,
                        duration_ms=round(duration * 1000, 2),
                    )
                raise e

        return wrapper

    return decorator


class Telemetry:
    """
    Facade for Logs, Metrics, and Tracing.
    """

    def __init__(self, component_name: str) -> None:
        self.component = component_name
        self.logger: logging.Logger
        self._setup_logger()

    def _setup_logger(self) -> None:
        """Initializes the logger. Safe to call multiple times."""
        self.logger = logging.getLogger(self.component)

        # Ensure we output to console if not configured
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def __getstate__(self) -> dict[str, Any]:
        """Pickling: Save everything EXCEPT the logger."""
        state = self.__dict__.copy()
        if "logger" in state:
            del state["logger"]
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
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

    def log_info(self, event: str, **kwargs: Any) -> None:
        trace_id = self.get_trace_id()
        msg = f"[{trace_id}] {event} | {kwargs}"
        self.logger.info(msg)

    def log_error(self, event: str, error: Exception, **kwargs: Any) -> None:
        trace_id = self.get_trace_id()
        msg = f"[{trace_id}] ❌ {event} | Error: {str(error)} | {kwargs}"
        self.logger.error(msg, exc_info=True)
