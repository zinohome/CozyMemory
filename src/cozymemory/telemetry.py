"""Optional OpenTelemetry instrumentation.

Enable by installing `pip install cozymemory[otel]` and setting:
  OTEL_ENABLED=true
  OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
"""

import os

import structlog

logger = structlog.get_logger(__name__)


def setup_telemetry(service_name: str = "cozymemory") -> None:
    if os.getenv("OTEL_ENABLED", "").lower() not in ("true", "1"):
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logger.warning(
            "OTEL_ENABLED=true but opentelemetry packages not installed. "
            "Install with: pip install cozymemory[otel]"
        )
        return

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument()
    HTTPXClientInstrumentor.instrument()

    logger.info("OpenTelemetry tracing initialized", service=service_name)
