# chatbot.py

from dotenv import load_dotenv
import os
from openai import OpenAI
import requests
import datetime
import json

# 1️⃣ Cargar variables del .env
load_dotenv()

# 2️⃣ Configurar OpenAI con la API Key usando la nueva API
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 3️⃣ Log de interacciones con MCP Server
log = []

# 4️⃣ Función para preguntar al LLM y mantener contexto
def ask_llm(prompt, context=""):
    messages = [
        {"role": "system", "content": "Eres un asistente inteligente y servicial."},
        {"role": "user", "content": context + "\n" + prompt}
    ]
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=200
        )
        return response.choices[0].message.content
    except Exception as e:
        return "Lo siento, hubo un error con el LLM: " + str(e)

# 5️⃣ Función para llamar al MCP Server de vuelos
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

# 6️⃣ Función para mostrar el log
def show_log():
    print("\n=== LOG DE INTERACCIONES ===")
    print(json.dumps(log, indent=2))
    print("===========================\n")

# 7️⃣ Bucle principal del chatbot
def main():
    print("Bienvenido al Chatbot MCP Server 🚀")
    print("Escribe 'ver log' para mostrar el historial de interacciones")
    print("Escribe 'salir' para terminar la sesión\n")

    session_history = ""

    while True:
        user_input = input("Tú: ")

        if user_input.lower() in ["salir", "exit"]:
            print("¡Hasta luego! 👋")
            break
        elif user_input.lower() == "ver log":
            show_log()
            continue
        elif user_input.lower().startswith("buscar vuelo"):
            # Comando para buscar vuelos:
            # Ej: "buscar vuelo GUA PTY 2025-12-01"
            try:
                parts = user_input.split()
                origin = parts[2]
                destination = parts[3]
                departure_date = parts[4]
                flights = call_mcp_flights(origin, destination, departure_date)
                if flights.get("flights"):
                    print("\nVuelos encontrados:")
                    for f in flights["flights"]:
                        print(f"- {f['airline']} {f['flight_number']} | Salida: {f['departure_time']} | Llegada: {f['arrival_time']} | Estado: {f['status']}")
                        if "weather" in f:
                            print(f"  Clima en destino: {f['weather']['temperature']}°C, {f['weather']['condition']}")
                        if "activities" in f:
                            print("  Actividades sugeridas:")
                            for a in f["activities"]:
                                print(f"   * {a['name']} (Rating: {a['rating']})")
                    print()
                else:
                    print("No se encontraron vuelos para esa búsqueda.")
            except Exception:
                print("Formato incorrecto. Usa: buscar vuelo ORIGEN DESTINO FECHA")
            continue

        # Llamar al LLM
        response = ask_llm(user_input, context=session_history)
        print("Chatbot:", response)

        # Guardar interacción en contexto
        session_history += f"\nUser: {user_input}\nAssistant: {response}"

if __name__ == "__main__":
    main()
