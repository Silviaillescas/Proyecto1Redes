# chatbot.py

from dotenv import load_dotenv
import os
import openai
import requests
import datetime
import json
import re

# 1️⃣ Cargar variables del .env
load_dotenv()

# 2️⃣ Configurar OpenAI con la API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

# 3️⃣ Log de interacciones con MCP Server
log = []

# 4️⃣ Diccionario de IATA -> Ciudad
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

# 5️⃣ Mock de actividades por ciudad
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
    "New York": [
        {"name": "Times Square", "rating": 4.7},
        {"name": "Central Park", "rating": 4.8},
        {"name": "Metropolitan Museum of Art", "rating": 4.7}
    ],
    "Paris": [
        {"name": "Torre Eiffel", "rating": 4.9},
        {"name": "Museo del Louvre", "rating": 4.8},
        {"name": "Catedral de Notre Dame", "rating": 4.7}
    ],
    "Tokyo": [
        {"name": "Templo Senso-ji", "rating": 4.8},
        {"name": "Shibuya Crossing", "rating": 4.7},
        {"name": "Parque Ueno", "rating": 4.6}
    ]
}

# 6️⃣ Función para preguntar al LLM y mantener contexto
def ask_llm(prompt, context=""):
    try:
        messages = [
            {"role": "system", "content": "Eres un asistente inteligente y servicial."},
            {"role": "user", "content": context + "\n" + prompt}
        ]
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=200
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Lo siento, hubo un error con el LLM: {str(e)}"

# 7️⃣ Función para llamar al MCP Server de vuelos
def call_mcp_flights(origin, destination, departure_date):
    payload = {
        "origin": origin,
        "destination": destination,
        "departure_date": departure_date
    }
    try:
        response = requests.post("http://127.0.0.1:8000/get_flights", json=payload)
        result = response.json()
    except Exception:
        # Fallback: mock de vuelos si el servidor MCP no responde
        result = {"flights": []}

    # Guardar en log
    log.append({
        "timestamp": str(datetime.datetime.now()),
        "endpoint": "/get_flights",
        "request": payload,
        "response": result
    })

    return result

# 8️⃣ Función para obtener clima
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
            return {
                "temperature": data["main"]["temp"],
                "condition": data["weather"][0]["description"]
            }
        else:
            return {"temperature": 25, "condition": "sunny"}
    except:
        return {"temperature": 25, "condition": "sunny"}

# 9️⃣ Función para obtener actividades
def get_activities(iata_code):
    city = IATA_TO_CITY.get(iata_code)
    if not city:
        return []
    return CITY_ACTIVITIES.get(city, [])

# 🔟 Función para formatear la salida de vuelos
def format_flights(flights):
    if not flights:
        return "No se encontraron vuelos."

    output = "\nVuelos encontrados:\n"
    for f in flights:
        output += f"- {f['airline']} {f['flight_number']} | Salida: {f['departure_time']} | Llegada: {f['arrival_time']} | Estado: {f['status']}\n"
        output += f"  Clima en destino: {f['weather']['temperature']}°C, {f['weather']['condition']}\n"
        if f.get("activities"):
            output += "  Actividades sugeridas:\n"
            for act in f["activities"]:
                output += f"   - {act['name']} (Rating: {act['rating']})\n"
        output += "\n"
    return output

# 1️⃣1️⃣ Función para mostrar log
def show_log():
    print("\n=== LOG DE INTERACCIONES ===")
    print(json.dumps(log, indent=2))
    print("===========================\n")

# 1️⃣2️⃣ Función para parsear texto natural
def parse_flight_request(text):
    # Buscar fecha
    date_match = re.search(r"(\d{4}-\d{2}-\d{2}|\d{2}-\d{2}-\d{4})", text)
    if not date_match:
        return None
    date_str = date_match.group(0)

    # Convertir DD-MM-YYYY a YYYY-MM-DD
    if "-" in date_str and len(date_str.split("-")[0]) == 2:
        day, month, year = date_str.split("-")
        date_str = f"{year}-{month}-{day}"

    origin = None
    destination = None

    # Buscar ciudades ignorando "City" y mayúsculas
    for code, city in IATA_TO_CITY.items():
        city_name = city.replace(" City", "").lower()
        if city_name in text.lower():
            if not origin:
                origin = code
            elif code != origin:
                destination = code

    if not origin or not destination:
        return None

    return origin, destination, date_str

# 1️⃣3️⃣ Bucle principal
def main():
    print("Bienvenido al Chatbot MCP Server 🚀")
    print("Escribe 'ver log' para mostrar el historial de interacciones")
    print("Escribe 'salir' para terminar la sesión")
    print("Comando para vuelos: buscar vuelo ORIGEN DESTINO FECHA (YYYY-MM-DD)\n")

    session_history = ""

    while True:
        user_input = input("Tú: ")

        if user_input.lower() in ["salir", "exit"]:
            print("¡Hasta luego! 👋")
            break
        elif user_input.lower() == "ver log":
            show_log()
            continue
        elif "vuelo" in user_input.lower():
            flight_request = parse_flight_request(user_input)
            if flight_request:
                origin, destination, departure_date = flight_request
                flights_data = call_mcp_flights(origin, destination, departure_date)
                print(format_flights(flights_data.get("flights", [])))
            else:
                print("No pude interpretar la solicitud de vuelo. Usa formato: 'buscar vuelo ORIGEN DESTINO FECHA' o escribe claramente la ciudad y fecha.")
            continue

        # Llamar al LLM
        response = ask_llm(user_input, context=session_history)
        print("Chatbot:", response)

        # Guardar interacción en contexto
        session_history += f"\nUser: {user_input}\nAssistant: {response}"

if __name__ == "__main__":
    main()
