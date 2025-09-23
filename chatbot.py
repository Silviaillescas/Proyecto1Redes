# chatbot.py

from dotenv import load_dotenv
import os
from openai import OpenAI  # SDK nuevo
import requests
import datetime
import json
import re
import subprocess
import threading
import chess


# 1) Cargar variables del .env
load_dotenv()

# 2) Cliente OpenAI (toma OPENAI_API_KEY del entorno)
client = OpenAI()

# 3) Log de interacciones con MCP Server
log = []

# 4) Diccionario de IATA -> Ciudad
IATA_TO_CITY = {
    "GUA": "Guatemala City", "PTY": "Panama City", "SAL": "San Salvador",
    "SAP": "San Pedro Sula", "TGU": "Tegucigalpa", "SJO": "San Jose", "LIR": "Liberia",
    "MEX": "Mexico City", "CUN": "Cancun", "NYC": "New York", "LAX": "Los Angeles",
    "MIA": "Miami", "ORD": "Chicago", "BOG": "Bogota", "LIM": "Lima", "GRU": "Sao Paulo",
    "EZE": "Buenos Aires", "SCL": "Santiago", "CCS": "Caracas", "MAD": "Madrid",
    "BCN": "Barcelona", "LON": "London", "PAR": "Paris", "FRA": "Frankfurt",
    "HKG": "Hong Kong", "NRT": "Tokyo", "BKK": "Bangkok", "DEL": "Delhi", "SIN": "Singapore"
}

# 5) Mock de actividades por ciudad
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

# 6) Filesystem (RAM)
FILESYSTEM = {}

# 7) Función para preguntar al LLM (con contexto)
def ask_llm(prompt, context=""):
    try:
        if not os.getenv("OPENAI_API_KEY"):
            return "No se encontró OPENAI_API_KEY en el entorno (.env). Agrégala y vuelve a intentar."

        messages = [
            {"role": "system", "content": "Eres un asistente inteligente y servicial."},
            {"role": "user", "content": (context + "\n" + prompt).strip()}
        ]
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=200,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"Error del LLM: {type(e).__name__}: {str(e)}"

# 8) MCP Vuelos (tu FastAPI local)
def call_mcp_flights(origin, destination, departure_date):
    payload = {"origin": origin, "destination": destination, "departure_date": departure_date}
    try:
        response = requests.post("http://127.0.0.1:8000/get_flights", json=payload, timeout=8)
        result = response.json()
    except Exception as e:
        result = {"flights": [], "error": f"Fallo MCP flights: {str(e)}"}

    log.append({
        "timestamp": str(datetime.datetime.now()),
        "endpoint": "/get_flights",
        "request": payload,
        "response": result
    })
    return result

# 9) MCP Weather (no se usa directamente aquí; lo hace tu server de vuelos)
def get_weather(iata_code):
    city = IATA_TO_CITY.get(iata_code)
    if not city:
        return {"temperature": 25, "condition": "unknown city"}
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return {"temperature": 25, "condition": "sunny"}
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        data = requests.get(url, timeout=8).json()
        if "main" in data and "weather" in data:
            return {"temperature": data["main"]["temp"], "condition": data["weather"][0]["description"]}
        else:
            return {"temperature": 25, "condition": "sunny"}
    except Exception:
        return {"temperature": 25, "condition": "sunny"}

# 10) MCP Actividades (mock)
def get_activities(iata_code):
    city = IATA_TO_CITY.get(iata_code)
    if not city:
        return []
    return CITY_ACTIVITIES.get(city, [])

# 11) Formatear vuelos
def format_flights(flights):
    if not flights:
        return "No se encontraron vuelos."
    output = "\nVuelos encontrados:\n"
    for f in flights:
        airline = f.get('airline', 'N/D')
        number = f.get('flight_number', 'N/D')
        dtime = f.get('departure_time', 'N/D')
        atime = f.get('arrival_time', 'N/D')
        status = f.get('status', 'N/D')
        weather = f.get('weather', {}) or {}
        temp = weather.get('temperature', 'N/D')
        cond = weather.get('condition', 'N/D')

        output += f"- {airline} {number} | Salida: {dtime} | Llegada: {atime} | Estado: {status}\n"
        output += f"  Clima en destino: {temp}°C, {cond}\n"

        acts = f.get("activities") or []
        if acts:
            output += "  Actividades sugeridas:\n"
            for act in acts:
                output += f"   - {act.get('name','N/D')} (Rating: {act.get('rating','N/D')})\n"
        output += "\n"
    return output

# 12) Mostrar log
def show_log():
    print("\n=== LOG DE INTERACCIONES ===")
    print(json.dumps(log, indent=2, ensure_ascii=False))
    print("===========================\n")

# 13) Parsear vuelo (texto libre)
def parse_flight_request(text):
    # Fecha: YYYY-MM-DD o DD-MM-YYYY
    date_match = re.search(r"(\d{4}-\d{2}-\d{2}|\d{2}-\d{2}-\d{4})", text)
    if not date_match:
        return None
    date_str = date_match.group(0)
    # Normalizar a YYYY-MM-DD si viene DD-MM-YYYY
    if "-" in date_str and len(date_str.split("-")[0]) == 2:
        day, month, year = date_str.split("-")
        date_str = f"{year}-{month}-{day}"

    origin = None
    destination = None
    text_low = text.lower()

    for code, city in IATA_TO_CITY.items():
        city_name = city.replace(" City", "").lower()
        if city_name in text_low:
            if not origin:
                origin = code
            elif code != origin and not destination:
                destination = code

    if not origin or not destination:
        return None
    return origin, destination, date_str

# 14) MCP Filesystem (crear/leer/listar) — robusto con comillas
def filesystem_create(command: str) -> str:
    """
    Formatos aceptados:
      - crear archivo NOMBRE CONTENIDO...
      - crear archivo "NOMBRE CON ESPACIOS" CONTENIDO...
    """
    m = re.match(r'^crear\s+archivo\s+"([^"]+)"\s+(.+)$', command, re.IGNORECASE)
    if not m:
        m = re.match(r'^crear\s+archivo\s+(\S+)\s+(.+)$', command, re.IGNORECASE)
    if not m:
        return "Formato incorrecto. Usa: crear archivo NOMBRE CONTENIDO (puedes usar comillas para nombres con espacios)"

    filename, content = m.group(1), m.group(2)
    FILESYSTEM[filename] = content
    return f"Archivo '{filename}' creado en MCP Filesystem."

def filesystem_read(command: str) -> str:
    """
    Formatos aceptados:
      - leer archivo NOMBRE
      - leer archivo "NOMBRE CON ESPACIOS"
    """
    m = re.match(r'^leer\s+archivo\s+"([^"]+)"\s*$', command, re.IGNORECASE)
    if not m:
        m = re.match(r'^leer\s+archivo\s+(\S+)\s*$', command, re.IGNORECASE)
    if not m:
        return "Formato incorrecto. Usa: leer archivo NOMBRE (puedes usar comillas para nombres con espacios)"

    filename = m.group(1)
    if filename not in FILESYSTEM:
        return f"No se encontró el archivo {filename}"
    return f"Contenido de {filename}:\n{FILESYSTEM[filename]}"

def filesystem_list() -> str:
    nombres = sorted(FILESYSTEM.keys())
    return f"Archivos en MCP Filesystem: {nombres}"

# 15) MCP Git real (repositorio local aislado)
# --- GIT helpers ---
GIT_REPO_PATH = os.path.abspath("./mcp_git_repo")

def _ensure_git_repo():
    os.makedirs(GIT_REPO_PATH, exist_ok=True)
    if not os.path.exists(os.path.join(GIT_REPO_PATH, ".git")):
        # crea rama main directamente (evita 'master')
        subprocess.run(["git", "init", "-b", "main"], cwd=GIT_REPO_PATH, check=True)
        subprocess.run(["git", "config", "user.name", "MCP Bot"], cwd=GIT_REPO_PATH, check=True)
        subprocess.run(["git", "config", "user.email", "mcp-bot@example.com"], cwd=GIT_REPO_PATH, check=True)
        with open(os.path.join(GIT_REPO_PATH, ".gitignore"), "a", encoding="utf-8") as f:
            f.write("\n# MCP defaults\nmcp-env/\n__pycache__/\n*.pyc\n.env\n")

def git_commit_real(command: str) -> str:
    """
    Soporta:
      git commit ARCHIVO MENSAJE...
      git commit "ARCHIVO CON ESPACIOS" "MENSAJE con espacios"
    """
    # 1) con comillas en ambos
    m = re.match(r'^git\s+commit\s+"([^"]+)"\s+"([^"]+)"\s*$', command, re.IGNORECASE)
    # 2) con comillas sólo en archivo
    if not m:
        m = re.match(r'^git\s+commit\s+"([^"]+)"\s+(.+)$', command, re.IGNORECASE)
    # 3) sin comillas
    if not m:
        m = re.match(r'^git\s+commit\s+(\S+)\s+(.+)$', command, re.IGNORECASE)

    if not m:
        return 'Formato incorrecto. Usa: git commit ARCHIVO MENSAJE  (acepta comillas)'

    filename, message = m.group(1), m.group(2)

    try:
        _ensure_git_repo()

        file_path = os.path.join(GIT_REPO_PATH, filename)
        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)

        # Si existe en FILESYSTEM, volcamos su contenido al repo
        contenido = FILESYSTEM.get(filename)
        if contenido is not None:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(contenido)
        else:
            # Si no existe en FS, crea el archivo si no está en disco
            if not os.path.exists(file_path):
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("")

        subprocess.run(["git", "add", filename], cwd=GIT_REPO_PATH, check=True)

        # Evitar commits vacíos
        has_changes = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=GIT_REPO_PATH)
        if has_changes.returncode == 0:
            return f"No hay cambios para commitear en '{filename}'. Edita el archivo o crea contenido con 'crear archivo ...'."

        subprocess.run(["git", "commit", "-m", message], cwd=GIT_REPO_PATH, check=True)

        log.append({
            "timestamp": str(datetime.datetime.now()),
            "endpoint": "MCP Git",
            "request": {"file": filename, "message": message},
            "response": "Commit realizado"
        })
        return f"Archivo '{filename}' agregado y commit realizado con mensaje: '{message}'"

    except subprocess.CalledProcessError as e:
        return f"Error en Git: {e}"
    except Exception as e:
        return f"Error general: {e}"

def git_set_remote(command: str) -> str:
    """
    git set-remote https://github.com/USUARIO/REPO.git
    """
    m = re.match(r'^git\s+set-remote\s+(\S+)\s*$', command, re.IGNORECASE)
    if not m:
        return "Formato incorrecto. Usa: git set-remote URL"

    url = m.group(1)
    try:
        _ensure_git_repo()
        # si ya existe origin, cambia url; si no, agrégalo
        remotes = subprocess.run(["git", "remote"], cwd=GIT_REPO_PATH, capture_output=True, text=True, check=True).stdout.split()
        if "origin" in remotes:
            subprocess.run(["git", "remote", "set-url", "origin", url], cwd=GIT_REPO_PATH, check=True)
        else:
            subprocess.run(["git", "remote", "add", "origin", url], cwd=GIT_REPO_PATH, check=True)
        return f"Remote 'origin' configurado a: {url}"
    except subprocess.CalledProcessError as e:
        return f"Error configurando remoto: {e}"
    except Exception as e:
        return f"Error general: {e}"

def git_push(command: str) -> str:
    """
    git push  (empuja rama main a origin)
    """
    if not re.match(r'^git\s+push\s*$', command, re.IGNORECASE):
        return "Comando no reconocido. Usa: git push"

    try:
        _ensure_git_repo()
        # crea main si aún no hay commit
        subprocess.run(["git", "branch", "-M", "main"], cwd=GIT_REPO_PATH, check=True)
        result = subprocess.run(["git", "push", "-u", "origin", "main"], cwd=GIT_REPO_PATH, capture_output=True, text=True)
        if result.returncode != 0:
            return f"Error al hacer push:\n{result.stdout}\n{result.stderr}"
        return "Push realizado a origin/main."
    except subprocess.CalledProcessError as e:
        return f"Error en push: {e}"
    except Exception as e:
        return f"Error general: {e}"


# 16) MCP Chess con Stockfish (interactivo)
STOCKFISH_PATH = r"C:\Users\Silvia\stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe"

def analyze_chess(command: str) -> str:
    """
    Formatos aceptados (texto del usuario):
      - analizar ajedrez <FEN>
      - analizar ajedrez <movidas SAN>  (e.g., 'e4 e5 Nf3 Nc6 Bb5')
    Internamente:
      - Para FEN se usa:   'position fen <fen>'
      - Para movidas SAN:  se convierten a UCI y luego 'position startpos moves <...>'
    """
    parts = command.split(maxsplit=2)
    if len(parts) < 3:
        return "Formato incorrecto. Usa: analizar ajedrez FEN/PGN (ej. 'analizar ajedrez e4 e5 Nf3 ...')"

    payload = parts[2].strip()

    if not os.path.exists(STOCKFISH_PATH):
        return f"No encuentro Stockfish en: {STOCKFISH_PATH}. Verifica la ruta."

    # Heurística simple para detectar FEN (tiene 6 campos y barras '/')
    # Nota: también hay FEN válidos sin '/', pero esto cubre la mayoría de casos prácticos.
    def looks_like_fen(text: str) -> bool:
        return (text.count(" ") >= 5) and ("/" in text or text.split()[0].count("/") == 7)

    # Si NO es FEN, intentamos interpretar como secuencia SAN y convertir a UCI
    def san_to_uci_moves(san_seq: str):
        board = chess.Board()  # startpos
        uci_moves = []
        # Admite tokens tipo "1.", "1...", "+", "#" mezclados (los filtramos)
        tokens = [t for t in san_seq.replace("\n", " ").split() if not t.endswith(".") and not t.replace(".", "").isdigit()]
        for tok in tokens:
            # Limpia anotaciones de mate/jaque o comentarios simples
            tok_clean = tok.replace("+", "").replace("#", "")
            # ignora resultados tipo 1-0, 0-1, 1/2-1/2
            if tok_clean in ("1-0", "0-1", "1/2-1/2", "*"):
                break
            move = board.parse_san(tok_clean) if tok_clean else None  # parse SAN
            board.push(move)
            uci_moves.append(move.uci())
        return uci_moves

    try:
        # Prepara comando UCI para Stockfish
        if looks_like_fen(payload):
            position_cmd = f"position fen {payload}"
        else:
            try:
                uci_moves = san_to_uci_moves(payload)
                if not uci_moves:
                    return "No pude convertir las movidas a UCI. Escribe movidas SAN válidas (ej.: 'e4 e5 Nf3 Nc6')."
                position_cmd = "position startpos moves " + " ".join(uci_moves)
            except Exception as conv_err:
                return f"Error convirtiendo SAN→UCI: {conv_err}"

        # Lanza Stockfish
        proc = subprocess.Popen(
            [STOCKFISH_PATH],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        def send(cmd: str):
            proc.stdin.write(cmd + "\n")
            proc.stdin.flush()

        # Arranque UCI y sincronización
        send("uci")
        send("isready")

        # Hilo lector: esperamos hasta 'bestmove'
        lines = []
        bestmove = None

        def reader():
            nonlocal bestmove
            for line in proc.stdout:
                line = line.strip()
                lines.append(line)
                if line.startswith("bestmove"):
                    bestmove = line
                    break

        # Set position y pensar
        send(position_cmd)
        send("go depth 12")

        t = threading.Thread(target=reader, daemon=True)
        t.start()
        t.join(timeout=10)  # tiempo máximo de espera

        # Intenta terminar el engine
        try:
            send("quit")
        except Exception:
            pass

        if bestmove:
            # Muestra últimas líneas 'info' para dar contexto
            infos = [ln for ln in lines if ln.startswith("info depth")]
            tail = "\n".join(infos[-5:])
            return f"{bestmove}\n\nÚltimas líneas de análisis:\n{tail}" if tail else bestmove

        # Si no obtuvimos bestmove a tiempo, forzamos cierre
        try:
            proc.kill()
        except Exception:
            pass
        return "No se obtuvo 'bestmove' a tiempo. Intenta con otra posición o baja la profundidad."

    except Exception as e:
        return f"Error al analizar partida de ajedrez: {str(e)}"


# 17) MCP Remoto - Hora actual (Cloudflare Worker o local)
def call_remote_time():
    try:
        WORKER_URL = os.getenv("MCP_TIME_URL", "http://127.0.0.1:8787/get_time")  
        response = requests.get(WORKER_URL, timeout=5)
        data = response.json()
        return {
            "date": data.get("date", "")[:10],
            "time": data.get("time", "")[:8],
            "timezone": data.get("timezone", "America/Guatemala")
        }
    except Exception as e:
        return {"error": str(e)}
    

def format_ext1_result(res: dict) -> str:
    if not isinstance(res, dict):
        return str(res)
    if "error" in res:
        return f"❌ Error: {res['error']}"
    lines = []
    lines.append(f"🔎 Conexiones totales: {res.get('total_connections', 0)}")
    lines.append(f"❗ Intentos fallidos: {res.get('failed_attempts', 0)}")
    sus = res.get('suspicious_ips') or []
    if sus:
        lines.append("🚩 IPs sospechosas:")
        for ip in sus:
            lines.append(f"   • {ip}")
    else:
        lines.append("🚩 IPs sospechosas: (ninguna)")
    lines.append(f"🧱 Posible fuerza bruta: {res.get('possible_bruteforce', False)}")
    rep = res.get('ip_reputation') or {}
    if rep:
        lines.append("📚 Reputación IP:")
        for ip, info in rep.items():
            lines.append(f"   • {ip}: {info}")
    return "\n".join(lines)

def start_log_capture():
    global LOG_CAPTURE, LOG_BUFFER
    LOG_CAPTURE = True
    LOG_BUFFER = []
    return "📝 Modo captura de log ON. Pega líneas; escribe 'fin log' para analizar."

def end_log_capture():
    global LOG_CAPTURE, LOG_BUFFER
    if not LOG_BUFFER:
        LOG_CAPTURE = False
        return "No capturé líneas. Modo captura OFF."
    text = "\n".join(LOG_BUFFER)
    LOG_CAPTURE = False
    from mcp_clients import ext1_analyze_log_text
    res = ext1_analyze_log_text(text)
    LOG_BUFFER = []
    return "📊 Resultado (lote):\n" + format_ext1_result(res)


# 18) Bucle principal
def main():
    print("Bienvenido al Chatbot MCP Server 🚀")
    print("Escribe 'ver log' para mostrar el historial de interacciones")
    print("Escribe 'salir' para terminar la sesión")
    print("Comando para vuelos: buscar vuelo ORIGEN DESTINO FECHA (YYYY-MM-DD)")
    print("Comando para MCP Filesystem: crear archivo NOMBRE CONTENIDO | crear archivo \"NOMBRE CON ESPACIOS\" CONTENIDO")
    print("                           leer archivo NOMBRE | leer archivo \"NOMBRE CON ESPACIOS\" | listar archivos")
    print("Comando para MCP Git: git commit NOMBRE_ARCHIVO MENSAJE")
    print("Comando para MCP Chess: analizar ajedrez FEN/PGN")
    print("Comando para MCP Remoto: hora actual")
    print("Comandos para MCP Externo 1: estado ext1 | analiza log: TEXTO | hora y estado\n")

    session_history = ""

    while True:
        user_input = input("Tú: ")

        if user_input.lower() in ["salir", "exit"]:
            print("¡Hasta luego! 👋")
            break

        if user_input.lower() == "ver log":
            show_log()
            continue

        if user_input.lower().startswith("buscar vuelo"):
            flight_request = parse_flight_request(user_input)
            if flight_request:
                origin, destination, departure_date = flight_request
                flights_data = call_mcp_flights(origin, destination, departure_date)
                print(format_flights(flights_data.get("flights", [])))
            else:
                print("No pude interpretar la solicitud de vuelo. Usa formato: 'buscar vuelo ORIGEN DESTINO FECHA'")
            continue

        if user_input.lower().startswith("crear archivo"):
            print(filesystem_create(user_input))
            continue

        if user_input.lower().startswith("leer archivo"):
            print(filesystem_read(user_input))
            continue

        if user_input.lower() == "listar archivos":
            print(filesystem_list())
            continue

        if user_input.lower().startswith("git commit"):
            print(git_commit_real(user_input))
            continue

        if user_input.lower().startswith("analizar ajedrez"):
            print(analyze_chess(user_input))
            continue

        if user_input.lower().startswith("hora actual"):
            print("Consultando al MCP remoto de hora...")
            print(call_remote_time())
            continue

        # === NUEVOS COMANDOS: MCP EXTERNO 1 (logs del compañero) ===
        if user_input.lower() == "estado ext1":
            from mcp_clients import ext1_status
            print("Consultando estado del MCP externo 1...")
            print(ext1_status())
            continue

        if user_input.lower().startswith("analiza log:"):
            from mcp_clients import ext1_analyze_log_text
            log_text = user_input.split(":", 1)[1].strip()
            if log_text:
                print("Enviando log al MCP externo 1...")
                res = ext1_analyze_log_text(log_text)
                print(format_ext1_result(res))              
            else:
                print("Debes escribir algo después de 'analiza log:'")
            continue

        if user_input.lower() == "hora y estado":
            from mcp_clients import get_remote_time, ext1_status
            print("Consultando MCP remoto de hora y MCP externo 1...")
            hora = get_remote_time()
            estado = ext1_status()
            print("🕒 Hora GT:", hora)
            print("📡 Estado ext1:", estado)
            continue

        # === Default: LLM con contexto ===
        response = ask_llm(user_input, context=session_history)
        print("Chatbot:", response)
        session_history += f"\nUser: {user_input}\nAssistant: {response}"
            # En el banner
            
        print("Comandos MCP Externo 2 (MoodST/Spotify):")
        print("  estado moodst | spotify conectar | spotify completar URL_COMPLETA | spotify buscar: TEXTO")

        # En el while True:
        if user_input.lower() == "estado moodst":
            from mcp_clients import ext2_status
            print("Consultando MoodST adapter...")
            print(ext2_status())
            continue

        if user_input.lower() == "spotify conectar":
            from mcp_clients import ext2_auth_begin
            res = ext2_auth_begin()
            url = (res or {}).get("authorize_url") or (res or {}).get("url") or res
            print("Abre en el navegador y autoriza:", url)
            print("Luego usa: spotify completar URL_COMPLETA")
            continue

        if user_input.lower().startswith("spotify completar "):
            from mcp_clients import ext2_auth_complete
            redirect_url = user_input.split(" ", 2)[2].strip()
            print(ext2_auth_complete(redirect_url))
            continue

        if user_input.lower().startswith("spotify buscar:"):
            from mcp_clients import ext2_search_track
            q = user_input.split(":", 1)[1].strip()
            print(ext2_search_track(q, limit=5))
            continue



if __name__ == "__main__":
    main()
