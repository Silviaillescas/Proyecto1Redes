# remote_mcp.py
from fastapi import FastAPI
from datetime import datetime
import pytz  # Asegúrate de instalarlo: pip install pytz

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Servidor MCP remoto activo 🚀"}

@app.get("/get_time")
def get_time():
    tz = pytz.timezone("America/Guatemala")  # Zona horaria confiable en Windows
    guatemala_now = datetime.now(tz)
    return {
        "date": guatemala_now.strftime("%Y-%m-%d"),
        "time": guatemala_now.strftime("%H:%M:%S"),
        "timezone": str(guatemala_now.tzinfo)
    }
