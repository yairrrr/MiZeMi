"""Single-worker local/Render entrypoint: python -m app."""
import uvicorn
from app.infrastructure.settings import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, workers=1,
                log_level=settings.log_level.lower(), ws="websockets",
                ws_max_size=65_536, ws_ping_interval=20, ws_ping_timeout=20,
                timeout_graceful_shutdown=25, access_log=False)
