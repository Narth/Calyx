"""Run the telemetry gateway: python -m cbo_hub.telemetry_gateway"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "cbo_hub.telemetry_gateway.app:app",
        host="0.0.0.0",
        port=7781,
        log_level="info",
    )
