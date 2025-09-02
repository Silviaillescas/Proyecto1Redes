from fastapi import FastAPI
from pydantic import BaseModel
import requests
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

class FlightRequest(BaseModel):
    origin: str
    destination: str
    departure_date: str

# Diccionario de IATA -> Ciudad
IATA_TO_CITY = {
    "GUA": "Guatemala City",
    "PTY": "Panama City",
    "NYC": "New York",
    "PAR": "Paris",
    "LON": "London",
    # ... agrega más ciudades según tu mock
}

# Mock de actividades por ciudad
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
    ]
}

# Función para obtener clima
def get_weather(iata_code):
    city = IATA_TO_CITY.get(iata_code)
    if not city:
        return {"temperature": 25, "condition": "unknown city"}

    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return {"temperature": 25, "condition": "sunny"}

    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        response = requests.get(url)
        data = response.json()
        if "main" in data and "weather" in data:
            return {"temperature": data["main"]["temp"], "condition": data["weather"][0]["description"]}
        else:
            return {"temperature": 25, "condition": "sunny"}
    except:
        return {"temperature": 25, "condition": "sunny"}

def get_activities(iata_code):
    city = IATA_TO_CITY.get(iata_code)
    if not city:
        return []
    return CITY_ACTIVITIES.get(city, [])

@app.post("/get_flights")
def get_flights(request: FlightRequest):
    api_key = os.getenv("AVIATIONSTACK_API_KEY")
    url = f"http://api.aviationstack.com/v1/flights?access_key={api_key}&dep_iata={request.origin}&arr_iata={request.destination}&flight_date={request.departure_date}"

    try:
        response = requests.get(url)
        data = response.json()
    except:
        data = {"data": []}

    flights = []

    if data.get("data"):
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
        # Mock si la API falla o no hay datos
        flights = [
            {
                "flight_number": "CM123",
                "airline": "Copa Airlines",
                "departure_airport": request.origin,
                "departure_time": f"{request.departure_date}T08:30:00",
                "arrival_airport": request.destination,
                "arrival_time": f"{request.departure_date}T10:00:00",
                "status": "scheduled",
                "weather": get_weather(request.destination),
                "activities": get_activities(request.destination)
            },
            {
                "flight_number": "AV456",
                "airline": "Avianca",
                "departure_airport": request.origin,
                "departure_time": f"{request.departure_date}T12:00:00",
                "arrival_airport": request.destination,
                "arrival_time": f"{request.departure_date}T13:30:00",
                "status": "scheduled",
                "weather": get_weather(request.destination),
                "activities": get_activities(request.destination)
            }
        ]

    return {"flights": flights}
