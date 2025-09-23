Silvia Illescas #22376
---

# Proyecto 1 – MCP Chatbot

## 📌 Descripción

Este proyecto implementa un **chatbot anfitrión** que interactúa con **servidores MCP locales y remotos** usando el protocolo JSON-RPC. El chatbot mantiene contexto en la conversación y registra un **log de todas las interacciones**.

* **Servidor MCP local:** obtiene información de **vuelos** y **clima**.
* **Servidor MCP remoto:** devuelve la **hora actual de Guatemala** a través de un túnel de Cloudflare.

---

## 🛠 Tecnologías

* **Python 3.11+**
* **FastAPI** – Servidor MCP remoto
* **Requests** – Comunicación con servidores y APIs externas
* **Dotenv** – Variables de entorno
* **Wireshark** – Análisis de tráfico de red
* **APIs externas:**

  * AviationStack (vuelos)
  * OpenWeather (clima)
* **Cloudflare Tunnel (cloudflared)** – Para exponer el servidor remoto

---

## 🚀 Instalación

1. Clonar el repositorio:

```bash
git clone https://github.com/Silviaillescas/Proyecto1Redes.git
cd Proyecto1Redes
```

2. Crear y activar un entorno virtual:

```bash
python -m venv mcp-env
mcp-env\Scripts\activate   # Windows
```

3. Instalar dependencias:

```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuración de Servidores MCP

### 1. Servidor MCP Local

* Implementado en FastAPI.
* Expone endpoints para vuelos y clima.
* Se ejecuta con:

```bash
uvicorn mcp_local:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Servidor MCP Remoto (Hora actual)

Archivo: `remote_mcp.py`

Levantar el servidor en **puerto 8787**:

```bash
uvicorn remote_mcp:app --host 127.0.0.1 --port 8787 --reload
```

Probar localmente:

```bash
curl "http://127.0.0.1:8787/get_time?tz=America/Guatemala"
```

---

## 🌐 Exposición con Cloudflare Tunnel

### Quick Tunnel (modo rápido)

En otra terminal:

```bash
cloudflared tunnel --url http://127.0.0.1:8787
```

Se generará una URL pública como:

```
https://ejemplo.trycloudflare.com
```

Probar:

```bash
curl "https://ejemplo.trycloudflare.com/get_time?tz=America/Guatemala"
```

### Configuración en el chatbot

Editar el archivo `.env` en la raíz del proyecto:

```env
MCP_TIME_URL=https://ejemplo.trycloudflare.com/get_time?tz=America/Guatemala
```

El chatbot leerá esta variable automáticamente al iniciar.

---

## 🔄 Manejo cuando expira el túnel

Los **quick tunnels** de Cloudflare expiran cuando cierras la terminal o al cabo de unas horas. Para mantenerlo funcionando:

1. Vuelve a ejecutar:

   ```bash
   uvicorn remote_mcp:app --host 127.0.0.1 --port 8787 --reload
   cloudflared tunnel --url http://127.0.0.1:8787
   ```
2. Copia la nueva URL pública (`https://nuevo.trycloudflare.com`).
3. Actualiza tu `.env` con esa URL.
4. Reinicia el chatbot.

### Opción avanzada: túnel permanente

Si no quieres cambiar la URL cada vez:

* Crea un túnel nombrado con `cloudflared login` y `cloudflared tunnel create`.
* Asóciale un subdominio estable de Cloudflare.
* Configura `config.yml` para que siempre apunte a `http://127.0.0.1:8787`.
* Corre `cloudflared tunnel run <nombre>`.
  Así tu chatbot tendrá una URL fija que nunca caduca.

---

## 📊 Análisis de tráfico

Puedes usar **Wireshark** para capturar:

* Handshake TCP/TLS del túnel.
* Llamadas JSON-RPC entre el chatbot y el servidor MCP remoto.

---

## ▶️ Ejecución del Chatbot

Con todo configurado:

```bash
python chatbot.py
```

El chatbot ahora podrá:

* Consultar vuelos y clima vía MCP local.
* Obtener la hora de Guatemala vía MCP remoto expuesto con Cloudflare.

---

os y demostrativos.

