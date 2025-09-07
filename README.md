# Proyecto1Redes
Silvia Illescas #22376

# MCP Server - Entrega Parcial

## Objetivo

El MCP Server permite a agentes LLM obtener información de vuelos, clima y actividades para planificar itinerarios.  
Utiliza APIs externas cuando es posible y mocks cuando la información no está disponible.

---

## Tecnologías utilizadas

- Python 3.9
- FastAPI
- Uvicorn
- Requests
- python-dotenv
- Pydantic

---

## Variables de entorno

Crear un archivo `.env` en la raíz del proyecto con las siguientes claves:

AVIATIONSTACK_API_KEY=TU_API_KEY_AVIATIONSTACK
OPENWEATHER_API_KEY=TU_API_KEY_OPENWEATHER


> **Importante:** No subir `.env` a GitHub. Añadirlo a `.gitignore`.

---

## Cómo ejecutar

1. Activar entorno virtual:

```bash
# Windows PowerShell
.\mcp-env\Scripts\activate


Instalar dependencias:

pip install -r requirements.txt


Ejecutar servidor:

uvicorn server:app --reload


Abrir Swagger UI para probar:

http://127.0.0.1:8000/docs

Ejemplo de request
POST /get_flights
{
  "origin": "GUA",
  "destination": "PTY",
  "departure_date": "2025-12-01"
}

Ejemplo de response
{
  "flights": [
    {
      "flight_number": "CM123",
      "airline": "Copa Airlines",
      "departure_airport": "GUA",
      "departure_time": "2025-12-01T08:30:00",
      "arrival_airport": "PTY",
      "arrival_time": "2025-12-01T10:00:00",
      "status": "scheduled",
      "weather": {
        "temperature": 29.46,
        "condition": "moderate rain"
      },
      "activities": [
        {"name": "Canal de Panamá", "rating": 4.8},
        {"name": "Casco Viejo", "rating": 4.6},
        {"name": "Biomuseo", "rating": 4.5}
      ]
    }
  ]
}

Mock vs Datos reales

Vuelos: Se obtienen de Aviationstack cuando hay API Key y datos disponibles.

Clima: Se obtiene de OpenWeather o se mockea si falla la API.

Actividades: Mock locales por ciudad usando CITY_ACTIVITIES.

Precios: No disponibles en el plan free de Aviationstack.

Observaciones

Este MCP Server corresponde a la Entrega Parcial (Paso 5 del proyecto).

Está preparado para ser integrado con agentes LLM que consuman los datos y generen itinerarios.
