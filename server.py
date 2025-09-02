from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI()

# Modelo para recibir los datos del viaje
class FlightRequest(BaseModel):
    origin: str
    destination: str
    departure_date: str

# Ruta principal que consulta la API de Aviationstack
@app.post("/get_flights")
def get_flights(request: FlightRequest):
    api_key = "TU_API_KEY_AVIATIONSTACK"  # Sustituir con tu API Key

    # Endpoint de Aviationstack para vuelos programados
    url = f"http://api.aviationstack.com/v1/flights?access_key={api_key}&dep_iata={request.origin}&arr_iata={request.destination}&flight_date={request.departure_date}"

    try:
        response = requests.get(url)
        data = response.json()
    except Exception as e:
        return {"error": f"No se pudo obtener la información de vuelos: {e}"}

    # Extraemos la información más relevante
    flights = []
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

    return {"flights": flights}
