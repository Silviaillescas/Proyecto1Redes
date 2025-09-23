# server.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from dotenv import load_dotenv
import os
from datetime import datetime
from typing import Dict, Any, Optional, Union, List

# Cargar variables de entorno
load_dotenv()

app = FastAPI(title="MCP Flight Server", version="1.0")

# (Opcional) CORS si se llama desde navegador/Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======== Modelos ========

# REST
class FlightRequest(BaseModel):
    origin: str
    destination: str
    departure_date: str  # puede ser YYYY-MM-DD o DD/MM/YYYY

# JSON-RPC
class RPCReq(BaseModel):
    jsonrpc: str
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[int, str]] = None

# ======== Datos base ========

IATA_TO_CITY = {
    # Centroamérica
    "GUA": "Guatemala City",
    "PTY": "Panama City",
    "SAL": "San Salvador",
    "SAP": "San Pedro Sula",
    "TGU": "Tegucigalpa",
    "SJO": "San Jose",
    "LIR": "Liberia",
    # Norteamérica
    "MEX": "Mexico City",
    "CUN": "Cancun",
    "NYC": "New York",
    "LAX": "Los Angeles",
    "MIA": "Miami",
    "ORD": "Chicago",
    # Sudamérica
    "BOG": "Bogota",
    "LIM": "Lima",
    "GRU": "Sao Paulo",
    "EZE": "Buenos Aires",
    "SCL": "Santiago",
    "CCS": "Caracas",
    # Europa
    "MAD": "Madrid",
    "BCN": "Barcelona",
    "LON": "London",
    "PAR": "Paris",
    "FRA": "Frankfurt",
    "AMS": "Amsterdam",
    "ROM": "Rome",
    "BER": "Berlin",
    "MXP": "Milan",
    # Asia
    "HKG": "Hong Kong",
    "NRT": "Tokyo",
    "BKK": "Bangkok",
    "DEL": "Delhi",
    "SIN": "Singapore",
    "ICN": "Seoul",
}

CITY_ACTIVITIES = {
    "Guatemala City": [
        {"name": "Museo Nacional de Arqueología", "rating": 4.6},
        {"name": "Parque Central", "rating": 4.4},
        {"name": "Catedral Metropolitana", "rating": 4.5},
    ],
    "Panama City": [
        {"name": "Canal de Panamá", "rating": 4.8},
        {"name": "Casco Viejo", "rating": 4.6},
        {"name": "Biomuseo", "rating": 4.5},
    ],
    "Paris": [
        {"name": "Torre Eiffel", "rating": 4.9},
        {"name": "Museo del Louvre", "rating": 4.8},
        {"name": "Catedral de Notre Dame", "rating": 4.7},
    ],
    "New York": [
        {"name": "Times Square", "rating": 4.7},
        {"name": "Central Park", "rating": 4.8},
        {"name": "Metropolitan Museum of Art", "rating": 4.7},
    ],
    "Tokyo": [
        {"name": "Templo Senso-ji", "rating": 4.8},
        {"name": "Shibuya Crossing", "rating": 4.7},
        {"name": "Parque Ueno", "rating": 4.6},
    ],
}

# ======== Helpers internos (compartidos por REST y RPC) ========

def _normalize_date(d: str) -> str:
    """Normaliza a YYYY-MM-DD si viene como DD/MM/YYYY; si no, deja como está."""
    try:
        if "/" in d:
            return datetime.strptime(d, "%d/%m/%Y").strftime("%Y-%m-%d")
        return datetime.strptime(d, "%Y-%m-%d").strftime("%Y-%m-%d")
    except Exception:
        return d  # si no se puede parsear, se usa tal cual

def get_weather(iata_code: str) -> Dict[str, Any]:
    city = IATA_TO_CITY.get(iata_code)
    if not city:
        return {"temperature": None, "condition": "unknown city"}

    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return {"temperature": 25, "condition": "sunny"}  # mock si no hay API key

    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        r = requests.get(url, timeout=5)
        data = r.json()
        if "main" in data and "weather" in data:
            return {
                "temperature": round(data["main"]["temp"], 1),
                "condition": data["weather"][0]["description"],
            }
        return {"temperature": 25, "condition": "sunny"}
    except Exception:
        return {"temperature": 25, "condition": "sunny"}

def get_activities(iata_code: str) -> List[Dict[str, Any]]:
    city = IATA_TO_CITY.get(iata_code)
    if not city:
        return []
    return CITY_ACTIVITIES.get(city, [])

def _get_flights_core(origin: str, destination: str, departure_date: str) -> Dict[str, Any]:
    """Lógica principal para obtener vuelos (real + mock)."""
    departure_date = _normalize_date(departure_date)
    api_key = os.getenv("AVIATIONSTACK_API_KEY")
    url = (
        f"http://api.aviationstack.com/v1/flights"
        f"?access_key={api_key}&dep_iata={origin}&arr_iata={destination}&flight_date={departure_date}"
    )

    try:
        r = requests.get(url, timeout=5)
        data = r.json()
    except Exception:
        data = {"data": []}

    flights = []
    if data.get("data"):
        # Datos reales de la API
        for flight in data.get("data", []):
            arrival_iata = (flight.get("arrival") or {}).get("iata")
            flights.append({
                "flight_number": (flight.get("flight") or {}).get("iata"),
                "airline": (flight.get("airline") or {}).get("name"),
                "departure_airport": (flight.get("departure") or {}).get("iata"),
                "departure_time": (flight.get("departure") or {}).get("estimated"),
                "arrival_airport": arrival_iata,
                "arrival_time": (flight.get("arrival") or {}).get("estimated"),
                "status": flight.get("flight_status"),
                "weather": get_weather(arrival_iata),
                "activities": get_activities(arrival_iata),
            })
    else:
        # Mock de vuelos si falla la API o no hay datos
        flights = [
            {
                "flight_number": "CM123",
                "airline": "Copa Airlines",
                "departure_airport": origin,
                "departure_time": f"{departure_date}T08:30:00",
                "arrival_airport": destination,
                "arrival_time": f"{departure_date}T10:00:00",
                "status": "scheduled",
                "weather": get_weather(destination),
                "activities": get_activities(destination),
            },
            {
                "flight_number": "AV456",
                "airline": "Avianca",
                "departure_airport": origin,
                "departure_time": f"{departure_date}T12:00:00",
                "arrival_airport": destination,
                "arrival_time": f"{departure_date}T13:30:00",
                "status": "scheduled",
                "weather": get_weather(destination),
                "activities": get_activities(destination),
            },
        ]
    return {"flights": flights}

# ======== Endpoints ========

@app.post("/get_flights")
def get_flights(request: FlightRequest):
    """REST clásico (compatibilidad con tu bot actual)."""
    return _get_flights_core(request.origin, request.destination, request.departure_date)

@app.post("/rpc")
def rpc(req: RPCReq):
    """JSON-RPC 2.0 con método get_flights."""
    if req.jsonrpc != "2.0":
        return {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": req.id}
    try:
        if req.method == "get_flights":
            p = req.params or {}
            origin = p.get("origin")
            destination = p.get("destination")
            departure_date = p.get("departure_date")
            if not all([origin, destination, departure_date]):
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32602, "message": "Invalid params: origin, destination, departure_date son requeridos"},
                    "id": req.id,
                }
            result = _get_flights_core(origin, destination, departure_date)
            return {"jsonrpc": "2.0", "result": result, "id": req.id}

        if req.method in ("ping", "health"):
            return {"jsonrpc": "2.0", "result": "ok", "id": req.id}

        return {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": req.id}
    except Exception as e:
        return {"jsonrpc": "2.0", "error": {"code": -32000, "message": str(e)}, "id": req.id}

# Ejecutar:
#   uvicorn server:app --host 127.0.0.1 --port 8000
