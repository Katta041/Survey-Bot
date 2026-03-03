from src.core.telemetry import (
    Span,
    log_llm_call,
    log_sarvam_call,
    new_trace_id,
    estimate_cost
)

# This is a legacy shim to ensure compatibility with root-level scripts
# that haven't been migrated to modular imports yet.
