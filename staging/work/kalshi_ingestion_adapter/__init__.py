"""Staging-only read-only Kalshi ingestion adapter."""

from .adapter import (
    KalshiReadOnlyClient,
    ingest_live_market,
    ingest_manual_snapshot,
    normalize_snapshot_to_case,
)
from .models import (
    INGESTION_SCHEMA_VERSION,
    AdapterIngestionResult,
    KalshiCaseOverlay,
    KalshiRawMarketSnapshot,
    export_adapter_json_schemas,
)

__all__ = [
    "INGESTION_SCHEMA_VERSION",
    "AdapterIngestionResult",
    "KalshiCaseOverlay",
    "KalshiRawMarketSnapshot",
    "KalshiReadOnlyClient",
    "export_adapter_json_schemas",
    "ingest_live_market",
    "ingest_manual_snapshot",
    "normalize_snapshot_to_case",
]
