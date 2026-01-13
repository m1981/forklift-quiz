import structlog
import time
import logging
from functools import wraps
from typing import Optional

# --- Observability Imports ---
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from prometheus_client import Histogram, Counter

# --- 1. Configure Structlog ---
# This ensures logs are formatted as JSON and passed to the standard logger,
# which OTel is listening to (thanks to app.py configuration).
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,  # Merges OTel trace IDs automatically
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# --- 2. Define Global Metrics (Prometheus) ---
# These will appear in Grafana
METHOD_DURATION = Histogram(
    'app_method_duration_seconds',
    'Time spent in method',
    ['component', 'method']
)
ERROR_COUNT = Counter(
    'app_error_total',
    'Total errors',
    ['component', 'error_type']
)

# --- 3. OTel Tracer ---
tracer = trace.get_tracer("warehouse-quiz-app")


def measure_time(metric_name: str):
    """
    Commercial Grade Decorator:
    1. Starts an OTel Span (Tracing)
    2. Times the execution
    3. Records to Prometheus (Metrics)
    4. Logs structured event (Logging)
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Dynamic lookup: Get component name from the instance
            telemetry = getattr(self, 'telemetry', None)
            comp_name = telemetry.component if telemetry else "Unknown"

            # 1. Start OTel Span (Tracing)
            with tracer.start_as_current_span(metric_name) as span:
                span.set_attribute("component", comp_name)

                start = time.perf_counter()
                try:
                    result = func(self, *args, **kwargs)

                    # 2. Record Success Metric (Prometheus)
                    duration = time.perf_counter() - start
                    METHOD_DURATION.labels(component=comp_name, method=metric_name).observe(duration)

                    # 3. Log Success (Structlog)
                    # We use the structlog logger directly here
                    logger = structlog.get_logger()
                    logger.info(metric_name, duration_ms=round(duration * 1000, 2), component=comp_name)

                    return result

                except Exception as e:
                    # Record Error Metric
                    duration = time.perf_counter() - start
                    ERROR_COUNT.labels(component=comp_name, error_type=type(e).__name__).inc()

                    # Mark Span as Error in OTel
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR))

                    # Log Error
                    logger = structlog.get_logger()
                    logger.error(f"failed_{metric_name}", error=str(e), component=comp_name)
                    raise e

        return wrapper

    return decorator


class Telemetry:
    """
    A facade for the Three Pillars.
    Now delegates heavy lifting to Structlog and OTel.
    """

    def __init__(self, component_name: str):
        self.component = component_name
        # Bind the component name to all logs from this instance
        self.logger = structlog.get_logger().bind(component=component_name)

    @staticmethod
    def start_trace() -> str:
        """
        Returns the current OTel Trace ID for UI display.
        """
        span = trace.get_current_span()
        if span:
            ctx = span.get_span_context()
            if ctx.trace_id:
                return format(ctx.trace_id, "032x")
        return "no-trace"

    def log_info(self, event: str, **kwargs):
        """
        Log info. Structlog handles JSON formatting and Context.
        """
        self.logger.info(event, **kwargs)

    def log_error(self, event: str, error: Exception, **kwargs):
        """
        Log error. Structlog handles the stack trace.
        """
        self.logger.error(event, error=str(error), **kwargs)