Based on the text you provided and the "Commercial Grade" principles we are following, the **modern way** is **NOT** to use a specific Loki client (like `python-logging-loki`).

The modern, commercial-grade standard is **OpenTelemetry (OTLP)**.

### Why?
As your text mentions: *"Loki natively supports ingesting OpenTelemetry logs over HTTP."*

This means you don't need separate tools for Traces and Logs. You use the **same OTel Exporter** for both. Your application sends data in the OTLP format, and Grafana Cloud automatically splits it: Traces go to Tempo, and Logs go to Loki.

Here is how to implement this in your Python code without running an external agent like Grafana Alloy (which is great for Kubernetes, but overkill for a standalone Python app).

---

### Step 1: Install OTel Logging Dependencies

You need the OTel SDK for logging.

```bash
pip install opentelemetry-sdk opentelemetry-exporter-otlp
```

### Step 2: Update `app.py` to Configure Logging

We need to add a `LoggerProvider` alongside the `TracerProvider` we added earlier. This tells Python: "When a log happens, send it to Grafana via OTLP."

**Update your `configure_observability` function in `app.py`:**

```python
import os
import logging
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

# --- NEW IMPORTS FOR LOGGING ---
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

def configure_observability():
    # 1. Define Resource (Service Name)
    resource = Resource.create({"service.name": "warehouse-quiz-app"})
    
    # --- TRACING SETUP (Keep this) ---
    trace_provider = TracerProvider(resource=resource)
    otlp_trace_exporter = OTLPSpanExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
        headers=os.getenv("OTEL_EXPORTER_OTLP_HEADERS")
    )
    trace_provider.add_span_processor(BatchSpanProcessor(otlp_trace_exporter))
    trace.set_tracer_provider(trace_provider)

    # --- LOGGING SETUP (New) ---
    # 1. Create the Logger Provider
    logger_provider = LoggerProvider(resource=resource)
    
    # 2. Configure the Exporter (Sends logs to Grafana Loki via OTLP)
    otlp_log_exporter = OTLPLogExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
        headers=os.getenv("OTEL_EXPORTER_OTLP_HEADERS")
    )
    
    # 3. Add Processor (Batches logs for performance)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_log_exporter))
    set_logger_provider(logger_provider)

    # 4. Attach OTel Handler to Python's Root Logger
    # This captures all logs (including structlog if configured correctly)
    handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)
```

### Step 3: Update `telemetry.py` to Bridge Structlog

We need to ensure `structlog` passes its JSON data to the standard Python logger, which `OTel` is now listening to.

**Update `src/shared/telemetry.py`:**

```python
import structlog
import logging

# ... imports ...

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        # CRITICAL CHANGE: Render to JSON, but keep it as a string for the standard logger
        structlog.processors.JSONRenderer()
    ],
    # CRITICAL CHANGE: Use LoggerFactory instead of PrintLoggerFactory.
    # This sends structlog entries to the standard Python logging module.
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# ... rest of the file ...
```

### Step 4: Environment Variables (Grafana Cloud)

You need to get your OTLP credentials from Grafana Cloud.

1.  Log in to **Grafana Cloud**.
2.  Go to **"OpenTelemetry"** -> **"Configure"**.
3.  You will see environment variables like this. Export them in your terminal:

```bash
# The Endpoint (Make sure it is the OTLP endpoint, NOT the Loki HTTP API endpoint)
export OTEL_EXPORTER_OTLP_ENDPOINT="https://otlp-gateway-prod-us-east-0.grafana.net"

# The Auth Header (Base64 encoded InstanceID:Token)
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic <YOUR_GENERATED_TOKEN>"

# Protocol (Optional, but good to be explicit)
export OTEL_EXPORTER_OTLP_PROTOCOL="grpc"
```

### Step 5: Verify in Grafana

1.  Run your app: `streamlit run app.py`.
2.  Generate some logs by clicking buttons.
3.  Go to Grafana Cloud -> **Explore**.
4.  Select **Loki** (Logs) from the dropdown.
5.  Run this query: `{service_name="warehouse-quiz-app"}`.

### Summary: Why is this "Commercial Grade"?

1.  **Unified Protocol:** You are not using a proprietary Loki client. You are using OTLP. If you switch from Grafana to Datadog or New Relic tomorrow, you just change the `ENDPOINT` environment variable. You don't change your code.
2.  **Performance:** The `BatchLogRecordProcessor` buffers logs and sends them in chunks, rather than making an HTTP request for every single log line (which would slow down your app).
3.  **Correlation:** Because OTel handles both Traces and Logs, Grafana will automatically link them. You can view a Trace and click "Logs for this span" to see the exact logs generated during that operation.