import os
import requests

# ========= MCP REMOTO – Hora GT =========
# También puedes dar fallback local separando por comas en la var:
# MCP_TIME_URL="https://.../get_time?tz=America/Guatemala,http://127.0.0.1:8787/get_time?tz=America/Guatemala"
_MCP_TIME_URLS = [u.strip() for u in os.getenv(
    "MCP_TIME_URL",
    "http://127.0.0.1:8787/get_time?tz=America/Guatemala"
).split(",") if u.strip()]

def get_remote_time():
    """Devuelve dict con date, time, timezone. Intenta varias URLs si se configuran."""
    last_err = None
    for url in _MCP_TIME_URLS:
        try:
            r = requests.get(url, timeout=6, headers={"Accept": "application/json"})
            r.raise_for_status()
            data = r.json()
            # Formatos admitidos: tu FastAPI (date/time) o Workers con {time:"...Z"}:
            if "date" in data and "time" in data:
                return {
                    "date": data.get("date", "")[:10],
                    "time": data.get("time", "")[:8],
                    "timezone": data.get("timezone", "America/Guatemala"),
                }
            # Soporte por si llega {"time":"2025-09-23T03:28:58.707Z"}
            t = data.get("time")
            if t:
                from datetime import datetime, timezone
                from zoneinfo import ZoneInfo
                if t.endswith("Z"):
                    t = t.replace("Z", "+00:00")
                dt = datetime.fromisoformat(t)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                dt_gt = dt.astimezone(ZoneInfo("America/Guatemala"))
                return {
                    "date": dt_gt.strftime("%Y-%m-%d"),
                    "time": dt_gt.strftime("%H:%M:%S"),
                    "timezone": "America/Guatemala",
                }
            # Si llega otro formato:
            return {"error": "Formato inesperado", "raw": data}
        except Exception as e:
            last_err = str(e)
            continue
    return {"error": f"No pude obtener hora. Último error: {last_err}"}

import os, requests

EXT1_BASE = os.getenv("MCP_EXT1_BASE", "http://127.0.0.1:8001").rstrip("/")

def ext1_status():
    try:
        r = requests.get(f"{EXT1_BASE}/status", timeout=6)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def ext1_analyze_log_text(text: str):
    """
    Envía el texto como si fuera un archivo 'chat.log' a /analyze_log_file (multipart/form-data).
    """
    try:
        files = {"file": ("chat.log", text.encode("utf-8"), "text/plain")}
        r = requests.post(f"{EXT1_BASE}/analyze_log_file", files=files, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {r.status_code}", "body": r.text[:500]}
    except Exception as e:
        return {"error": str(e)}

# (Opcional) si quieres mandar un archivo real:
def ext1_analyze_log_file(path: str):
    try:
        with open(path, "rb") as f:
            files = {"file": (os.path.basename(path), f, "text/plain")}
            r = requests.post(f"{EXT1_BASE}/analyze_log_file", files=files, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}
