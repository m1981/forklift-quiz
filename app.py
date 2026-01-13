import os
import logging
import streamlit as st

# --- OTel & Observability Imports ---
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

# --- OTel Logging Imports ---
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

# --- Prometheus Import ---
from prometheus_client import start_http_server

# --- Application Imports ---
from src.quiz.adapters.sqlite_repository import SQLiteQuizRepository
from src.quiz.presentation.state_provider import StreamlitStateProvider
from src.quiz.application.service import QuizService
from src.quiz.presentation.viewmodel import QuizViewModel
from src.quiz.presentation.views import components, question_view, summary_view
from src.fsm import QuizState


# --- 1. Configure Observability (The "Commercial Grade" Setup) ---
def configure_observability():
    """
    Configures OpenTelemetry to send Traces and Logs to Grafana Cloud via OTLP.
    Starts a background Prometheus server for Metrics.
    """
    # Check if configuration is present in Environment Variables
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    headers = os.getenv("OTEL_EXPORTER_OTLP_HEADERS")

    if not endpoint or not headers:
        print("⚠️ Observability Warning: OTEL env vars not set. Telemetry will not be sent to Cloud.")
        return

    # Define the Service Name (This appears in Grafana)
    resource = Resource.create({"service.name": "warehouse-quiz-app"})

    # --- A. TRACING SETUP ---
    trace_provider = TracerProvider(resource=resource)
    otlp_trace_exporter = OTLPSpanExporter(endpoint=endpoint, headers=headers)
    trace_provider.add_span_processor(BatchSpanProcessor(otlp_trace_exporter))
    trace.set_tracer_provider(trace_provider)

    # --- B. LOGGING SETUP (Loki via OTLP) ---
    logger_provider = LoggerProvider(resource=resource)
    otlp_log_exporter = OTLPLogExporter(endpoint=endpoint, headers=headers)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_log_exporter))
    set_logger_provider(logger_provider)

    # Attach OTel Handler to Python's Root Logger
    # This captures all logs (including structlog) and sends them to OTel
    handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)

    # --- C. METRICS SETUP (Prometheus) ---
    # Start a background HTTP server to expose metrics at /metrics
    try:
        start_http_server(8000)
        print("✅ Prometheus Metrics server started on port 8000")
    except OSError:
        print("⚠️ Prometheus port 8000 already in use (likely Streamlit reload). Skipping.")


# --- 2. Bootstrap Application ---

# Initialize Observability ONCE per session
if "observability_configured" not in st.session_state:
    # Basic console logging for local dev fallback
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

    configure_observability()
    st.session_state.observability_configured = True


# --- 3. Dependency Injection (Composition Root) ---
@st.cache_resource
def get_service():
    # Infrastructure
    repo = SQLiteQuizRepository("data/quiz.db")
    # Application
    return QuizService(repo)


def main():
    st.set_page_config(page_title="Warehouse Quiz", layout="centered")
    components.apply_styles()

    # Wiring
    service = get_service()
    state_provider = StreamlitStateProvider()
    vm = QuizViewModel(service, state_provider)

    # --- 4. Sidebar & Global State ---
    # We get current state from VM to pre-select UI options
    current_user = state_provider.get('user_id', 'Daniel')
    current_mode = state_provider.get('current_mode', 'Daily Sprint')

    sel_user, sel_mode, do_reset = components.render_sidebar(current_user, current_mode)

    # Handle Sidebar Actions
    if do_reset:
        service.repository.reset_user_progress(sel_user)
        vm.reset()
        st.rerun()

    if sel_user != current_user or sel_mode != current_mode:
        vm.reset()  # Reset if settings change
        # We don't start immediately; we wait for user to click "Start" in IDLE state
        state_provider.set('user_id', sel_user)
        state_provider.set('current_mode', sel_mode)
        st.rerun()

    # --- 5. Main Router (FSM) ---
    state = vm.current_state

    if state == QuizState.IDLE:
        st.title("🎓 Warehouse Certification")
        st.info(f"Gotowy, {sel_user}?")
        if st.button("🚀 Start Quiz", type="primary"):
            vm.start_quiz(sel_mode, sel_user)
            st.rerun()

    elif state == QuizState.LOADING:
        with st.spinner("Ładowanie pytań..."):
            pass

    elif state == QuizState.QUESTION_ACTIVE:
        components.render_dashboard(vm.get_dashboard_config())
        question_view.render_active(vm)

    elif state == QuizState.FEEDBACK_VIEW:
        components.render_dashboard(vm.get_dashboard_config())
        question_view.render_feedback(vm)

    elif state == QuizState.SUMMARY:
        summary_view.render(vm)

    elif state == QuizState.EMPTY_STATE:
        st.warning("Brak pytań w tym trybie.")
        if st.button("Wróć"):
            vm.reset()
            st.rerun()


if __name__ == "__main__":
    main()