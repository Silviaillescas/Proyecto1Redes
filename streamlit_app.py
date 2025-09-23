# Streamlit UI para Proyecto1Redes
# Autor: Chatbot helper
# Requisitos (añade a requirements.txt si hace falta):
#   streamlit
#   requests
#   python-dotenv
#   chess (opcional, para el módulo de ajedrez) -> pip install chess
#
# Ejecutar:
#   streamlit run streamlit_app.py
#
# Esta UI consume:
# - MCP local de vuelos: POST http://127.0.0.1:8000/get_flights
# - MCP remoto de hora: GET  <URL>/get_time?tz=America/Guatemala  (o la URL completa en .env: MCP_TIME_URL)
# - MCP externo (compañero) de logs: GET /status, POST /analyze_log_file (multipart) en http://127.0.0.1:8001

import os
import json
import re
import datetime as dt
import subprocess
import threading
from typing import Dict, Any, List

import requests
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# --- Opcional para ajedrez ---
try:
    import chess 
except Exception:
    chess = None

load_dotenv()

# OpenAI client (requiere OPENAI_API_KEY en .env)
client = OpenAI()

st.set_page_config(page_title="MCP Chatbot – UI", page_icon="🤖", layout="wide")
st.title("🤖 Proyecto1Redes")
st.caption("Panel para orquestar MCPs: vuelos, hora (Cloudflare) y analizador de logs del compañero.")

# ==========================
# Sidebar – Configuración
# ==========================
with st.sidebar:
    st.header("⚙️ Config")
    FLIGHTS_URL = st.text_input(
        "MCP Local – get_flights URL",
        value=os.getenv("MCP_FLIGHTS_URL", "http://127.0.0.1:8000/get_flights"),
    )

    TIME_URL_DEFAULT = os.getenv("MCP_TIME_URL", "http://127.0.0.1:8787/get_time?tz=America/Guatemala")
    TIME_URL = st.text_input("MCP Remoto – Hora (URL completa)", value=TIME_URL_DEFAULT)

    EXT1_BASE = st.text_input("MCP Externo – Logs (base URL)", value=os.getenv("EXT1_URL", "http://127.0.0.1:8001"))
    EXT1_STATUS = f"{EXT1_BASE.rstrip('/')}/status"
    EXT1_ANALYZE = f"{EXT1_BASE.rstrip('/')}/analyze_log_file"

    # Git
    GIT_REPO_PATH = st.text_input("Ruta repo Git local", value=os.path.abspath("./mcp_git_repo"))

    # Ajedrez
    STOCKFISH_PATH = st.text_input("Ruta Stockfish (opcional)", value=os.getenv("STOCKFISH_PATH", ""))
    DEPTH = st.slider("Profundidad análisis (ajedrez)", 6, 20, 12)

    st.markdown("---")
    st.caption("Sugerencias: verifica que tus servicios estén activos: \n- uvicorn server.py :8000 (vuelos) \n- uvicorn remote_mcp.py :8787 y cloudflared (hora) \n- uvicorn del compañero :8001 (logs)")

# Estado de sesión para log y FS
if "ui_log" not in st.session_state:
    st.session_state.ui_log: List[Dict[str, Any]] = []
if "FS" not in st.session_state:
    st.session_state.FS: Dict[str, str] = {}

# ==========================
# Helpers (HTTP y utilidades)
# ==========================
TIMEOUT_S = 12

IATA_TO_CITY = {
    "GUA": "Guatemala City", "PTY": "Panama City", "SAL": "San Salvador",
    "SAP": "San Pedro Sula", "TGU": "Tegucigalpa", "SJO": "San Jose", "LIR": "Liberia",
    "MEX": "Mexico City", "CUN": "Cancun", "NYC": "New York", "LAX": "Los Angeles",
    "MIA": "Miami", "ORD": "Chicago", "BOG": "Bogota", "LIM": "Lima", "GRU": "Sao Paulo",
    "EZE": "Buenos Aires", "SCL": "Santiago", "CCS": "Caracas", "MAD": "Madrid",
    "BCN": "Barcelona", "LON": "London", "PAR": "Paris", "FRA": "Frankfurt",
    "HKG": "Hong Kong", "NRT": "Tokyo", "BKK": "Bangkok", "DEL": "Delhi", "SIN": "Singapore"
}


def ui_log_push(event: str, req: Any, resp: Any):
    st.session_state.ui_log.append({
        "ts": dt.datetime.now().isoformat(timespec="seconds"),
        "event": event,
        "request": req,
        "response": resp,
    })


def call_flights(origin: str, destination: str, date_str: str) -> Dict[str, Any]:
    payload = {"origin": origin, "destination": destination, "departure_date": date_str}
    try:
        r = requests.post(FLIGHTS_URL, json=payload, timeout=TIMEOUT_S)
        data = r.json()
    except Exception as e:
        data = {"flights": [], "error": f"Fallo MCP flights: {e}"}
    ui_log_push("get_flights", payload, data)
    st.session_state["last_flights"] = data
    return data


def call_time() -> Dict[str, Any]:
    try:
        r = requests.get(TIME_URL, timeout=TIMEOUT_S)
        data = r.json()
    except Exception as e:
        data = {"error": str(e)}
    ui_log_push("get_time", {"url": TIME_URL}, data)
    st.session_state["last_time"] = data
    return data


def ext1_status() -> Any:
    try:
        return requests.get(EXT1_STATUS, timeout=TIMEOUT_S).json()
    except Exception as e:
        return {"error": str(e)}


def ext1_analyze_text_as_file(text: str) -> Any:
    # Envía texto como archivo virtual UTF-8
    try:
        files = {"file": ("snippet.log", text.encode("utf-8"), "text/plain")}
        r = requests.post(EXT1_ANALYZE, files=files, timeout=TIMEOUT_S)
        res = r.json()
        # recordar último resultado del analizador de logs
        st.session_state["last_log_result"] = res
        return res
    except Exception as e:
        return {"error": str(e)}


def ext1_analyze_uploaded_file(uploaded) -> Any:
    try:
        files = {"file": (uploaded.name or "log.txt", uploaded.getvalue(), "text/plain")}
        r = requests.post(EXT1_ANALYZE, files=files, timeout=TIMEOUT_S)
        res = r.json()
        # recordar último resultado del analizador de logs
        st.session_state["last_log_result"] = res
        return res
    except Exception as e:
        return {"error": str(e)}


# ======= Git helpers (local) =======

def ensure_git_repo(repo_path: str):
    os.makedirs(repo_path, exist_ok=True)
    if not os.path.exists(os.path.join(repo_path, ".git")):
        subprocess.run(["git", "init", "-b", "main"], cwd=repo_path, check=True)
        subprocess.run(["git", "config", "user.name", "MCP Bot"], cwd=repo_path, check=True)
        subprocess.run(["git", "config", "user.email", "mcp-bot@example.com"], cwd=repo_path, check=True)
        with open(os.path.join(repo_path, ".gitignore"), "a", encoding="utf-8") as f:
            f.write("\n# MCP defaults\nmcp-env/\n__pycache__/\n*.pyc\n.env\n")


def git_commit_file(repo_path: str, filename: str, content: str, message: str) -> str:
    try:
        ensure_git_repo(repo_path)
        file_path = os.path.join(repo_path, filename)
        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        subprocess.run(["git", "add", filename], cwd=repo_path, check=True)
        # evitar commit vacío
        has_changes = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=repo_path)
        if has_changes.returncode == 0:
            return "No hay cambios para commitear."
        subprocess.run(["git", "commit", "-m", message], cwd=repo_path, check=True)
        return f"Commit OK: {message}"
    except subprocess.CalledProcessError as e:
        return f"Error Git: {e}"
    except Exception as e:
        return f"Error general: {e}"


# ======= Ajedrez (Stockfish UCI) =======

def analyze_chess_payload(payload: str, stockfish_path: str, depth: int = 12) -> str:
    if not chess:
        return "python-chess no está instalado. Ejecuta: pip install chess"
    if not stockfish_path or not os.path.exists(stockfish_path):
        return f"No encuentro Stockfish en: {stockfish_path}"

    def looks_like_fen(text: str) -> bool:
        return (text.count(" ") >= 5) and ("/" in text or text.split()[0].count("/") == 7)

    def san_to_uci_moves(san_seq: str):
        board = chess.Board()
        uci_moves = []
        tokens = [t for t in san_seq.replace("\n", " ").split() if not t.endswith(".") and not t.replace(".", "").isdigit()]
        for tok in tokens:
            tk = tok.replace("+", "").replace("#", "")
            if tk in ("1-0", "0-1", "1/2-1/2", "*"):
                break
            move = board.parse_san(tk)
            board.push(move)
            uci_moves.append(move.uci())
        return uci_moves

    # Construir comando position
    if looks_like_fen(payload):
        position_cmd = f"position fen {payload}"
    else:
        uci_moves = san_to_uci_moves(payload)
        if not uci_moves:
            return "No pude convertir movidas SAN a UCI."
        position_cmd = "position startpos moves " + " ".join(uci_moves)

    try:
        proc = subprocess.Popen(
            [stockfish_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1
        )
        def send(cmd: str):
            proc.stdin.write(cmd + "\n"); proc.stdin.flush()
        send("uci"); send("isready")
        lines = []
        bestmove = None
        def reader():
            nonlocal bestmove
            for line in proc.stdout:
                line = line.strip(); lines.append(line)
                if line.startswith("bestmove"):
                    bestmove = line; break
        send(position_cmd)
        send(f"go depth {depth}")
        t = threading.Thread(target=reader, daemon=True); t.start(); t.join(timeout=10)
        try: send("quit")
        except Exception: pass
        if bestmove:
            infos = [ln for ln in lines if ln.startswith("info depth")]
            tail = "\n".join(infos[-5:])
            return f"{bestmove}\n\n{tail}" if tail else bestmove
        try: proc.kill()
        except Exception: pass
        return "No se obtuvo 'bestmove' a tiempo."
    except Exception as e:
        return f"Error Stockfish: {e}"


# ======= LLM (Chat) =======

def build_context_text(include_flights: bool, include_time: bool, include_logs: bool) -> str:
    parts = []
    if include_flights and 'last_flights' in st.session_state:
        try:
            parts.append("### Últimos vuelos\n" + json.dumps(st.session_state['last_flights'], ensure_ascii=False))
        except Exception:
            parts.append("### Últimos vuelos (no serializable)")
    if include_time and 'last_time' in st.session_state:
        parts.append("### Hora GT\n" + json.dumps(st.session_state['last_time'], ensure_ascii=False))
    if include_logs and 'last_log_result' in st.session_state:
        parts.append("### Análisis de logs\n" + json.dumps(st.session_state['last_log_result'], ensure_ascii=False))
    return "\n\n".join(parts) if parts else "No hay datos recientes todavía."


def ask_llm_streamlit(question: str, context_text: str) -> str:
    try:
        if not os.getenv('OPENAI_API_KEY'):
            return "Configura OPENAI_API_KEY en tu .env o variables de entorno."
        messages = [
            {"role": "system", "content": "Eres un asistente que responde basándose en el contexto dado. Si algo no está en el contexto, dilo claramente."},
            {"role": "user", "content": f"Contexto:\n{context_text}\n\nPregunta: {question}"}
        ]
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            messages=messages,
            max_tokens=400,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"Error del LLM: {e}"

# ==========================
# Tabs de la UI
# ==========================
TAB_VUELOS, TAB_HORA, TAB_LOGS, TAB_FS, TAB_GIT, TAB_AJEDREZ, TAB_CHAT, TAB_LOG = st.tabs([
    "✈️ Vuelos", "🕒 Hora (GT)", "🗂️ Logs (compañero)", "🗃️ Filesystem", "🌿 Git", "♟️ Ajedrez", "💬 Chat LLM", "📜 Log UI"
])

# --- Vuelos ---
with TAB_VUELOS:
    st.subheader("Buscar vuelos (MCP local)")
    c1, c2, c3 = st.columns(3)
    with c1:
        origin = st.selectbox("Origen (IATA)", sorted(IATA_TO_CITY.keys()), index=sorted(IATA_TO_CITY.keys()).index("GUA"))
    with c2:
        dest = st.selectbox("Destino (IATA)", sorted(IATA_TO_CITY.keys()), index=sorted(IATA_TO_CITY.keys()).index("MIA"))
    with c3:
        fecha = st.date_input("Fecha de salida", value=dt.date.today()).strftime("%Y-%m-%d")
    if st.button("Buscar vuelos"):
        data = call_flights(origin, dest, fecha)
        if data.get("flights"):
            st.success(f"{len(data['flights'])} vuelos encontrados")
            try:
                st.dataframe(data["flights"])  # si es lista de dicts
            except Exception:
                st.json(data["flights"])
        else:
            st.warning("No se encontraron vuelos o hubo un error.")
            st.json(data)

# --- Hora GT ---
with TAB_HORA:
    st.subheader("Hora actual (Guatemala)")
    if st.button("Obtener hora"):
        res = call_time()
        if "error" in res:
            st.error(res["error"])            
        else:
            # Acepta distintos formatos: {date,time,timezone} o {datetime_iso}
            if "datetime_iso" in res:
                st.code(res["datetime_iso"])            
            else:
                st.code(f"{res.get('date','')} {res.get('time','')} ({res.get('timezone','')})")
            st.json(res)

# --- Logs del compañero ---
with TAB_LOGS:
    st.subheader("MCP externo (analizador de logs)")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Probar estado /status"):
            st.json(ext1_status())
    with c2:
        snippet = st.text_area("Pega una línea de log (se envía como archivo UTF-8)")
        if st.button("Analizar línea"):
            if snippet.strip():
                st.json(ext1_analyze_text_as_file(snippet))
            else:
                st.info("Escribe algo primero.")
    st.markdown("---")
    up = st.file_uploader("Sube un archivo de log (texto)", type=["log", "txt", "conf", "out"])    
    if st.button("Analizar archivo"):
        if up is not None:
            st.json(ext1_analyze_uploaded_file(up))
        else:
            st.info("Primero selecciona un archivo.")

# --- Filesystem (en memoria de la UI) ---
with TAB_FS:
    st.subheader("Filesystem (RAM en la UI)")
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("Nombre archivo (puede tener espacios)")
        content = st.text_area("Contenido")
        if st.button("Crear/Actualizar archivo"):
            if not name:
                st.warning("Pon un nombre.")
            else:
                st.session_state.FS[name] = content
                st.success(f"Archivo '{name}' guardado en memoria.")
    with c2:
        if st.session_state.FS:
            sel = st.selectbox("Leer archivo", list(st.session_state.FS.keys()))
            if st.button("Mostrar contenido"):
                st.code(st.session_state.FS.get(sel, ""))
        else:
            st.info("No hay archivos en memoria.")
    st.markdown("**Listado:**")
    st.write(sorted(st.session_state.FS.keys()))

# --- Git ---
with TAB_GIT:
    st.subheader("Git (repo local aislado)")
    g1, g2 = st.columns(2)
    with g1:
        gfile = st.text_input("Archivo dentro del repo (ej. notas/demo.txt)")
        gtext = st.text_area("Contenido a commitear (si vacío, crea archivo vacío)")
    with g2:
        gmsg = st.text_input("Mensaje de commit", value="Integración UI Streamlit")
        if st.button("git commit"):
            msg = git_commit_file(GIT_REPO_PATH, gfile or "demo.txt", gtext or "", gmsg)
            st.write(msg)
            st.caption(GIT_REPO_PATH)
    st.info("Para push remoto usa tu consola (git set-remote + git push). Aquí nos quedamos en local.")

# --- Ajedrez ---
with TAB_AJEDREZ:
    st.subheader("Analizar posición/jugada (Stockfish)")
    if not chess:
        st.warning("Instala 'chess' para activar este módulo: pip install chess")
    payload = st.text_area("FEN o movidas SAN (e.g., 'e4 e5 Nf3 Nc6 Bb5')")
    if st.button("Analizar"):
        if not payload.strip():
            st.info("Escribe una posición o secuencia de jugadas.")
        else:
            st.code(analyze_chess_payload(payload.strip(), STOCKFISH_PATH, depth=DEPTH))

# --- Chat LLM ---
with TAB_CHAT:
    st.subheader("Chat con IA sobre tus resultados")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    colA, colB, colC = st.columns(3)
    with colA:
        inc_f = st.checkbox("Incluir vuelos", True)
    with colB:
        inc_t = st.checkbox("Incluir hora GT", False)
    with colC:
        inc_l = st.checkbox("Incluir logs", False)
    ctx_text = build_context_text(inc_f, inc_t, inc_l)
    with st.expander("Ver contexto que se enviará", expanded=False):
        st.code(ctx_text)
    # historial
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    prompt = st.chat_input("Haz tu pregunta… (ej.: ¿cuál es el vuelo más temprano?)")
    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        answer = ask_llm_streamlit(prompt, ctx_text)
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.markdown(answer)
        ui_log_push("llm_chat", {"question": prompt}, {"answer": answer})

# --- Log de la UI ---
with TAB_LOG:
    st.subheader("Log de interacciones de la UI")
    if st.session_state.ui_log:
        st.json(st.session_state.ui_log)
    else:
        st.info("Sin eventos todavía.")
