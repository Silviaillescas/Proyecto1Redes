Silvia Illescas #22376

````markdown
# Proyecto 1 – MCP Chatbot

## Descripción
Este proyecto implementa un **chatbot anfitrión** que interactúa con **servidores MCP locales y remotos** usando el protocolo JSON-RPC. El chatbot mantiene contexto en la conversación y registra un **log de todas las interacciones**.  

- **Servidor MCP local:** obtiene vuelos y clima.  
- **Servidor MCP remoto:** devuelve la hora actual vía un túnel Cloudflare.  

---

## Tecnologías
- **Python 3.11+**  
- **FastAPI** – Servidor MCP local  
- **Requests** – Comunicación con servidores y APIs externas  
- **Dotenv** – Variables de entorno  
- **Wireshark** – Análisis de tráfico de red  
- **APIs externas:**  
  - AviationStack (vuelos)  
  - OpenWeather (clima)  

---

## Instalación
1. Clonar el repositorio:
```bash
git clone https://github.com/Silviaillescas/Proyecto1Redes.git
cd Proyecto1Redes
````

2. Crear entorno virtual:

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Instalar dependencias:

```bash
pip install -r requirements.txt
```

4. Crear archivo `.env` con tus claves:

```
AVIATIONSTACK_API_KEY=<tu_api_key>
OPENWEATHER_API_KEY=<tu_api_key>
OPENAI_API_KEY=<tu_api_key>
```

---

## Uso

### 1. Iniciar servidor MCP local

```bash
uvicorn server:app --reload
```

* Endpoint disponible: `POST /get_flights`
* Parámetros JSON:

```json
{
  "origin": "IATA del aeropuerto de salida",
  "destination": "IATA del aeropuerto de llegada",
  "departure_date": "YYYY-MM-DD"
}
```

### 2. Ejecutar chatbot

```bash
python chatbot.py
```

* Interactúa con el chatbot vía consola.
* Mantiene contexto de conversación.
* Llama a servidores MCP locales y remotos según la solicitud del usuario.

### 3. Ejemplo de interacción

```text
Usuario: buscar vuelo NYC MIA 2025-09-23
Chatbot: Vuelo CM123 de Copa Airlines sale de NYC a MIA a las 08:30 y llega a las 10:00. Clima: soleado 25°C. Actividades: Times Square, Central Park, Metropolitan Museum of Art.
```

---

## Servidores MCP implementados

### Servidor local – Vuelos y clima

* **Endpoint:** `/get_flights`
* **Método:** POST
* **Parámetros JSON:**

```json
{
  "origin": "IATA del aeropuerto de salida",
  "destination": "IATA del aeropuerto de llegada",
  "departure_date": "YYYY-MM-DD"
}
```

* **Respuesta JSON:** lista de vuelos con:

  * flight\_number
  * airline
  * departure\_airport
  * departure\_time
  * arrival\_airport
  * arrival\_time
  * status
  * weather
  * activities

### Servidor remoto – Hora actual

* **Endpoint:** `/get_time`
* **Método:** GET
* **Respuesta JSON:**

```json
{
  "current_time": "2025-09-22T16:30:00"
}
```

---

## Logs

* Cada interacción con los servidores MCP se registra en `log.json` con:

  * Timestamp
  * Endpoint consultado
  * Request y Response JSON

---

## Análisis de tráfico (Wireshark)

El análisis de Wireshark evidencia el ciclo completo de comunicación:

| Fase            | Paquetes          | Dirección          | Descripción                            | Tipo JSON-RPC      |
| --------------- | ----------------- | ------------------ | -------------------------------------- | ------------------ |
| Sincronización  | Handshake TCP/TLS | Cliente ↔ Servidor | Establecimiento de conexión segura     | Sincronización     |
| Solicitud       | Application Data  | Cliente → Servidor | Petición JSON-RPC (ej. GET /get\_time) | Solicitud/Petición |
| Respuesta       | Application Data  | Servidor → Cliente | JSON con información solicitada        | Respuesta          |
| Cierre conexión | FIN, ACK          | Cliente ↔ Servidor | Terminación TCP                        | —                  |

* Confirma que la comunicación cumple el protocolo MCP.
* TLS asegura cifrado de datos y seguridad de la información.

---

## Contribuciones

* Código y documentación desarrollados por **Silvia Illescas**.
* Uso permitido de librerías externas y APIs según necesidades del proyecto.

---

## Licencia

* Proyecto académico del curso **CC3067 Redes – UVG 2025**.
* Código para fines educativos y demostrativos.

