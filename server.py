# server.py
from fastapi import FastAPI
from pydantic import BaseModel
import requests
from dotenv import load_dotenv
import os
from datetime import datetime

# Cargar variables de entorno
load_dotenv()

app = FastAPI(title="MCP Flight Server", version="1.0")

# Modelo para recibir los datos de vuelo
class FlightRequest(BaseModel):
    origin: str
    destination: str
    departure_date: str  # puede ser YYYY-MM-DD o DD/MM/YYYY

# Diccionario ampliado de códigos IATA -> ciudad
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
    "ICN": "Seoul"
}

# Mock de actividades turísticas por ciudad
CITY_ACTIVITIES = {
    "Guatemala City": [
        {"name": "Museo Nacional de Arqueología", "rating": 4.6},
        {"name": "Parque Central", "rating": 4.4},
        {"name": "Catedral Metropolitana", "rating": 4.5}
    ],
    "Panama City": [
        {"name": "Canal de Panamá", "rating": 4.8},
        {"name": "Casco Viejo", "rating": 4.6},
        {"name": "Biomuseo", "rating": 4.5}
    ],
    "Paris": [
        {"name": "Torre Eiffel", "rating": 4.9},
        {"name": "Museo del Louvre", "rating": 4.8},
        {"name": "Catedral de Notre Dame", "rating": 4.7}
    ],
    "New York": [
        {"name": "Times Square", "rating": 4.7},
        {"name": "Central Park", "rating": 4.8},
        {"name": "Metropolitan Museum of Art", "rating": 4.7}
    ],
    "Tokyo": [
        {"name": "Templo Senso-ji", "rating": 4.8},
        {"name": "Shibuya Crossing", "rating": 4.7},
        {"name": "Parque Ueno", "rating": 4.6}
    ]
    # Puedes agregar más ciudades según el alcance del proyecto
}

# Función para obtener el clima de la ciudad
def get_weather(iata_code):
    city = IATA_TO_CITY.get(iata_code)
    if not city:
        return {"temperature": None, "condition": "unknown city"}

    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return {"temperature": 25, "condition": "sunny"}  # mock si no hay API key

    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        response = requests.get(url, timeout=5)
        data = response.json()
        if "main" in data and "weather" in data:
            return {
                "temperature": round(data["main"]["temp"], 1),
                "condition": data["weather"][0]["description"]
            }
        else:
            return {"temperature": 25, "condition": "sunny"}
    except Exception:
        return {"temperature": 25, "condition": "sunny"}

# Función para obtener actividades según la ciudad
def get_activities(iata_code):
    city = IATA_TO_CITY.get(iata_code)
    if not city:
        return []
    return CITY_ACTIVITIES.get(city, [])

# Endpoint principal de MCP Server para vuelos
@app.post("/get_flights")
def get_flights(request: FlightRequest):
    # Validar fecha y normalizar a YYYY-MM-DD
    try:
        if "/" in request.departure_date:
            dt = datetime.strptime(request.departure_date, "%d/%m/%Y")
        else:
            dt = datetime.strptime(request.departure_date, "%Y-%m-%d")
        departure_date = dt.strftime("%Y-%m-%d")
    except Exception:
        departure_date = request.departure_date

    api_key = os.getenv("AVIATIONSTACK_API_KEY")
    url = f"http://api.aviationstack.com/v1/flights?access_key={api_key}&dep_iata={request.origin}&arr_iata={request.destination}&flight_date={departure_date}"

    try:
        response = requests.get(url, timeout=5)
        data = response.json()
    except:
        data = {"data": []}

    flights = []

    if data.get("data"):
        # Datos reales de la API
        for flight in data.get("data", []):
            arrival_iata = flight.get("arrival", {}).get("iata")
            flights.append({
                "flight_number": flight.get("flight", {}).get("iata"),
                "airline": flight.get("airline", {}).get("name"),
                "departure_airport": flight.get("departure", {}).get("iata"),
                "departure_time": flight.get("departure", {}).get("estimated"),
                "arrival_airport": arrival_iata,
                "arrival_time": flight.get("arrival", {}).get("estimated"),
                "status": flight.get("flight_status"),
                "weather": get_weather(arrival_iata),
                "activities": get_activities(arrival_iata)
            })
    else:
        # Mock de vuelos si falla la API o no hay datos
        flights = [
            {
                "flight_number": "CM123",
                "airline": "Copa Airlines",
                "departure_airport": request.origin,
                "departure_time": f"{departure_date}T08:30:00",
                "arrival_airport": request.destination,
                "arrival_time": f"{departure_date}T10:00:00",
                "status": "scheduled",
                "weather": get_weather(request.destination),
                "activities": get_activities(request.destination)
            },
            {
                "flight_number": "AV456",
                "airline": "Avianca",
                "departure_airport": request.origin,
                "departure_time": f"{departure_date}T12:00:00",
                "arrival_airport": request.destination,
                "arrival_time": f"{departure_date}T13:30:00",
                "status": "scheduled",
                "weather": get_weather(request.destination),
                "activities": get_activities(request.destination)
            }
        ]

    return {"flights": flights}
