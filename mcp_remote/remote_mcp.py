# remote_mcp.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import pytz

app = FastAPI(title="MCP Remote Time")

# (Opcional) CORS si tu chatbot llama desde navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # acótalo a tus dominios si quieres
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_TZ = "America/Guatemala"

def _safe_tz(tz_name: str):
    try:
        return pytz.timezone(tz_name)
    except Exception:
        return pytz.timezone(DEFAULT_TZ)

@app.get("/")
def root():
    return {"message": "Servidor MCP remoto activo 🚀", "endpoint": "/get_time"}

@app.get("/get_time")
def get_time(tz: str = Query(DEFAULT_TZ, description="IANA TZ, ej. America/Guatemala")):
    tzinfo = _safe_tz(tz)
    now = datetime.now(tzinfo)
    # Offset en formato ±HH:MM
    offset = now.strftime("%z")
    offset = f"{offset[:3]}:{offset[3:]}" if offset else "+00:00"

    return {
        "timezone": tz,  # devolvemos el nombre solicitado, no la repr de pytz
        "datetime_iso": now.strftime("%Y-%m-%dT%H:%M:%S") + offset,
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "utc_offset": offset
    }

# Ejecutar: uvicorn remote_mcp:app --host 127.0.0.1 --port 8000
