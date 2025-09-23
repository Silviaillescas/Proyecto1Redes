# remote_mcp.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Union, Dict, Any
import pytz

app = FastAPI(title="MCP Remote Time")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     
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

def _time_payload(tz_name: str) -> Dict[str, Any]:
    tzinfo = _safe_tz(tz_name)
    now = datetime.now(tzinfo)
    # Offset en formato ±HH:MM
    offset = now.strftime("%z")
    offset = f"{offset[:3]}:{offset[3:]}" if offset else "+00:00"
    return {
        "timezone": tz_name,  # devolvemos el nombre solicitado, no la repr de pytz
        "datetime_iso": now.strftime("%Y-%m-%dT%H:%M:%S") + offset,
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "utc_offset": offset,
    }

@app.get("/")
def root():
    return {"message": "Servidor MCP remoto activo 🚀", "endpoints": ["/get_time", "/rpc"]}

# === REST clásico (lo que ya usabas) ===
@app.get("/get_time")
def get_time(tz: str = Query(DEFAULT_TZ, description="IANA TZ, ej. America/Guatemala")):
    return _time_payload(tz)

# === JSON-RPC 2.0 minimalista en /rpc ===
class RPCReq(BaseModel):
    jsonrpc: str
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[int, str]] = None

@app.post("/rpc")
def rpc(req: RPCReq):
    # Validación base del envelope
    if req.jsonrpc != "2.0":
        return {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": req.id}
    try:
        # Métodos disponibles
        if req.method == "get_time":
            tz = (req.params or {}).get("tz", DEFAULT_TZ)
            return {"jsonrpc": "2.0", "result": _time_payload(tz), "id": req.id}

        if req.method in ("ping", "health"):
            return {"jsonrpc": "2.0", "result": "ok", "id": req.id}

        # Método no encontrado
        return {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": req.id}
    except Exception as e:
        # Error genérico del servidor
        return {"jsonrpc": "2.0", "error": {"code": -32000, "message": str(e)}, "id": req.id}

# Ejecutar
#   uvicorn remote_mcp:app --host 127.0.0.1 --port 8787   
