# remote_mcp.py
from fastapi import FastAPI
import datetime

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Servidor MCP remoto activo 🚀"}

@app.get("/get_time")
def get_time():
    now = datetime.datetime.now()
    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "timezone": str(now.astimezone().tzinfo)
    }
