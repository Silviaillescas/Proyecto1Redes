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

# Ruta principal del MCP Server
@app.post("/get_flights")
def get_flights(request: FlightRequest):
    api_key = os.getenv("AVIATIONSTACK_API_KEY")

    # Endpoint de Aviationstack
    url = f"http://api.aviationstack.com/v1/flights?access_key={api_key}&dep_iata={request.origin}&arr_iata={request.destination}&flight_date={request.departure_date}"

    try:
        response = requests.get(url)
        data = response.json()
    except Exception as e:
        return {"error": f"No se pudo obtener la información de vuelos: {e}"}

    flights = []

    # Si la API devuelve datos, los usamos
    if data.get("data"):
        for flight in data.get("data", []):
            flights.append({
                "flight_number": flight.get("flight", {}).get("iata"),
                "airline": flight.get("airline", {}).get("name"),
                "departure_airport": flight.get("departure", {}).get("airport"),
                "departure_time": flight.get("departure", {}).get("estimated"),
                "arrival_airport": flight.get("arrival", {}).get("airport"),
                "arrival_time": flight.get("arrival", {}).get("estimated"),
                "status": flight.get("flight_status")
            })
    else:
        # Si no hay datos reales, usamos un mock para pruebas
        flights = [
            {
                "flight_number": "CM123",
                "airline": "Copa Airlines",
                "departure_airport": request.origin,
                "departure_time": f"{request.departure_date}T08:30:00",
                "arrival_airport": request.destination,
                "arrival_time": f"{request.departure_date}T10:00:00",
                "status": "scheduled"
            },
            {
                "flight_number": "AV456",
                "airline": "Avianca",
                "departure_airport": request.origin,
                "departure_time": f"{request.departure_date}T12:00:00",
                "arrival_airport": request.destination,
                "arrival_time": f"{request.departure_date}T13:30:00",
                "status": "scheduled"
            }
        ]

    return {"flights": flights}
