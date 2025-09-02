from fastapi import FastAPI
from pydantic import BaseModel
import requests
from dotenv import load_dotenv
import os

# Cargar variables desde .env
load_dotenv()

app = FastAPI()

# Modelo para recibir datos del viaje
class FlightRequest(BaseModel):
    origin: str
    destination: str
    departure_date: str

# Diccionario de IATA -> Ciudad
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
    # Asia
    "HKG": "Hong Kong",
    "NRT": "Tokyo",
    "BKK": "Bangkok",
    "DEL": "Delhi",
    "SIN": "Singapore"
}

# Función para obtener clima desde OpenWeather
def get_weather(iata_code):
    city = IATA_TO_CITY.get(iata_code)
    if not city:
        return {"temperature": 25, "condition": "unknown city"}

    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        # Mock si no hay API Key
        return {"temperature": 25, "condition": "sunny"}

    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        response = requests.get(url)
        data = response.json()

        if "main" in data and "weather" in data:
            return {
                "temperature": data["main"]["temp"],
                "condition": data["weather"][0]["description"]
            }
        else:
            # Mock si la API falla
            return {"temperature": 25, "condition": "sunny"}

    except Exception:
        # Mock si ocurre cualquier error de conexión
        return {"temperature": 25, "condition": "sunny"}

# Ruta principal del MCP Server
@app.post("/get_flights")
def get_flights(request: FlightRequest):
    api_key = os.getenv("AVIATIONSTACK_API_KEY")

    # Endpoint de Aviationstack
    url = f"http://api.aviationstack.com/v1/flights?access_key={api_key}&dep_iata={request.origin}&arr_iata={request.destination}&flight_date={request.departure_date}"

    try:
        response = requests.get(url)
        data = response.json()
    except Exception:
        # Si falla la API, usamos mock
        data = {"data": []}

    flights = []

    if data.get("data"):
        # Usamos vuelos reales si los hay
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
                "weather": get_weather(arrival_iata)
            })
    else:
        # Mock de vuelos si no hay datos reales
        flights = [
            {
                "flight_number": "CM123",
                "airline": "Copa Airlines",
                "departure_airport": request.origin,
                "departure_time": f"{request.departure_date}T08:30:00",
                "arrival_airport": request.destination,
                "arrival_time": f"{request.departure_date}T10:00:00",
                "status": "scheduled",
                "weather": get_weather(request.destination)
            },
            {
                "flight_number": "AV456",
                "airline": "Avianca",
                "departure_airport": request.origin,
                "departure_time": f"{request.departure_date}T12:00:00",
                "arrival_airport": request.destination,
                "arrival_time": f"{request.departure_date}T13:30:00",
                "status": "scheduled",
                "weather": get_weather(request.destination)
            }
        ]

    return {"flights": flights}
