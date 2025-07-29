from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import cohere
from pyngrok import ngrok
import os
import urllib.parse
import sqlite3
from http import cookies
import secrets

# Configuración ngrok y Cohere (usa tus claves reales)
ngrok.set_auth_token("30IUO0tKAb6INPbCEIRBCj9N4fW_46F1JyMvuoUw8ik1pDefC")
API_KEY_COHERE = 'tEiSQlInoBfW2U1gtSgElZaNHbookFyGzLI2Vuuz'
co = cohere.Client(API_KEY_COHERE)

# Base de datos para usuarios
DB_PATH = "users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    # NUEVA TABLA PARA GUARDAR CHATS POR USUARIO
    c.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            mode TEXT NOT NULL,
            title TEXT,
            messages TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Directorio base donde están los HTML
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Diccionario para sesiones: session_id -> usuario
sessions = {}

class UnifiedHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _send_headers(self, status=200, content_type='text/html'):
        self.send_response(status)
        self.send_header('Content-type', content_type)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        # Nueva ruta para obtener usuario en sesión
        if self.path == '/api/session':
            cookie_header = self.headers.get('Cookie')
            user_session = None
            if cookie_header:
                cookie = cookies.SimpleCookie()
                cookie.load(cookie_header)
                if 'session_id' in cookie:
                    session_id = cookie['session_id'].value
                    user_session = sessions.get(session_id)
            self._send_headers(200, 'application/json')
            self.wfile.write(json.dumps({'usuario': user_session}).encode('utf-8'))
            return

        # NUEVA RUTA PARA OBTENER EL HISTORIAL DE CHATS DEL USUARIO LOGUEADO
        if self.path == '/api/history':
            cookie_header = self.headers.get('Cookie')
            user_session = None
            if cookie_header:
                cookie = cookies.SimpleCookie()
                cookie.load(cookie_header)
                if 'session_id' in cookie:
                    session_id = cookie['session_id'].value
                    user_session = sessions.get(session_id)
            if not user_session:
                self._send_headers(401, 'application/json')
                self.wfile.write(json.dumps({'error': 'No autenticado'}).encode('utf-8'))
                return

            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT id, mode, title, messages, created_at FROM chats WHERE username=? ORDER BY created_at ASC", (user_session,))
            rows = c.fetchall()
            conn.close()

            chats = []
            for row in rows:
                chat_id, mode, title, messages_json, created_at = row
                try:
                    messages = json.loads(messages_json)
                except Exception:
                    messages = []
                title = title or ''  # <-- CORRECCIÓN AÑADIDA para evitar None
                chats.append({
                    'id': chat_id,
                    'mode': mode,
                    'title': title,
                    'msgs': messages,
                    'created_at': created_at
                })

            self._send_headers(200, 'application/json')
            self.wfile.write(json.dumps({'chats': chats}).encode('utf-8'))
            return

        # Sirve index.html o registro.html según ruta
        if self.path in ['/', '/index.html']:
            filepath = os.path.join(BASE_DIR, 'index.html')
        elif self.path == '/registro.html':
            filepath = os.path.join(BASE_DIR, 'registro.html')
        elif self.path == '/menu.html':
            filepath = os.path.join(BASE_DIR, 'menu.html')  # NUEVA RUTA AGREGADA
        else:
            self.send_response(404)
            self.end_headers()
            return
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(content)
        except Exception:
            self.send_response(500)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')

        # APIs para chatbot IA
        if self.path == '/api/chat':
            data = json.loads(post_data)
            messages = data.get('messages', [])
            mode = data.get('mode', 'general')
            chat_id = data.get('chat_id')  # <-- aquí el cambio para manejar chat_id
            title = data.get('title', '')   # <-- añadido para recibir título
            prompt = get_prompt_by_mode(mode)
            full_prompt = build_prompt(messages, prompt)
            try:
                response = co.generate(
                    model='command-r-plus',
                    prompt=full_prompt,
                    max_tokens=350,
                    temperature=0.75,
                    k=0,
                    p=0.75,
                    frequency_penalty=0,
                    presence_penalty=0,
                    stop_sequences=["--"],
                )
                answer = response.generations[0].text.strip()
            except Exception:
                answer = "Error al obtener respuesta de Cohere."

            # Agregar respuesta IA al arreglo messages antes de guardar
            messages.append({'text': answer, 'sender': 'bot'})

            # Guardar chat actualizado en la base de datos si usuario autenticado
            cookie_header = self.headers.get('Cookie')
            user_session = None
            if cookie_header:
                cookie = cookies.SimpleCookie()
                cookie.load(cookie_header)
                if 'session_id' in cookie:
                    session_id = cookie['session_id'].value
                    user_session = sessions.get(session_id)

            if user_session:
                try:
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    chat_json = json.dumps(messages, ensure_ascii=False)
                    if chat_id:  # Actualizar chat existente con título
                        # NUEVA LÓGICA PARA CONSERVAR EL TÍTULO SI NO SE ENVÍA UNO NUEVO
                        if not title:
                            c.execute("SELECT title FROM chats WHERE id=? AND username=?", (chat_id, user_session))
                            row = c.fetchone()
                            if row:
                                title = row[0]
                        c.execute(
                            "UPDATE chats SET mode=?, messages=?, title=? WHERE id=? AND username=?",
                            (mode, chat_json, title, chat_id, user_session)
                        )
                    else:  # Crear chat nuevo con título
                        c.execute(
                            "INSERT INTO chats (username, mode, title, messages) VALUES (?, ?, ?, ?)",
                            (user_session, mode, title, chat_json)
                        )
                        chat_id = c.lastrowid  # Obtener ID chat nuevo
                    conn.commit()
                    conn.close()
                except Exception as e:
                    print(f"Error guardando chat en DB: {e}")

            self.send_response(200)
            self._send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"message": answer, "chat_id": chat_id}).encode('utf-8'))
            return

        elif self.path == '/api/title':
            data = json.loads(post_data)
            messages = data.get('messages', [])
            chat_id = data.get('chat_id')  # <-- añadido para actualizar título
            if messages:
                text = messages[0].get('text', '')
                try:
                    prompt = f"Resume en 2 a 4 palabras el tema principal del siguiente mensaje: {text}\nTítulo:"
                    response = co.generate(
                        model='command-r-plus',
                        prompt=prompt,
                        max_tokens=10,
                        temperature=0.5,
                        k=0,
                        p=0.75,
                        frequency_penalty=0,
                        presence_penalty=0,
                        stop_sequences=["\n"],
                    )
                    title = response.generations[0].text.strip()
                except Exception:
                    title = ''
            else:
                title = ''

            # Actualizar título en DB si chat_id y usuario logueado
            cookie_header = self.headers.get('Cookie')
            user_session = None
            if cookie_header:
                cookie = cookies.SimpleCookie()
                cookie.load(cookie_header)
                if 'session_id' in cookie:
                    session_id = cookie['session_id'].value
                    user_session = sessions.get(session_id)

            if user_session and chat_id:
                try:
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    c.execute(
                        "UPDATE chats SET title=? WHERE id=? AND username=?",
                        (title, chat_id, user_session)
                    )
                    conn.commit()
                    conn.close()
                except Exception as e:
                    print(f"Error actualizando título en DB: {e}")

            self.send_response(200)
            self._send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"title": title}).encode('utf-8'))
            return

        # Registro e inicio de sesión
        elif self.path == '/':
            post_vars = urllib.parse.parse_qs(post_data)
            usuario = post_vars.get('usuario', [None])[0]
            password = post_vars.get('password', [None])[0]
            action = post_vars.get('action', [None])[0]

            if not usuario or not password or not action:
                self._send_headers(400, 'application/json')
                self.wfile.write(json.dumps({'error': 'Faltan campos obligatorios'}).encode())
                return

            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()

            if action == 'login':
                c.execute("SELECT password FROM users WHERE username=?", (usuario,))
                row = c.fetchone()
                if row and row[0] == password:
                    # Crear sesión y enviar cookie
                    session_id = secrets.token_hex(16)
                    sessions[session_id] = usuario

                    # Obtener chats del usuario con títulos
                    c.execute("SELECT id, mode, title, messages, created_at FROM chats WHERE username=? ORDER BY created_at ASC", (usuario,))
                    rows = c.fetchall()
                    chats = []
                    for chat_id, mode, title, messages_json, created_at in rows:
                        try:
                            messages = json.loads(messages_json)
                        except Exception:
                            messages = []
                        title = title or ''  # <-- CORRECCIÓN AÑADIDA para evitar None
                        chats.append({
                            'id': chat_id,
                            'mode': mode,
                            'title': title,
                            'msgs': messages,
                            'created_at': created_at
                        })

                    self.send_response(200)
                    self._send_cors_headers()
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Set-Cookie', f'session_id={session_id}; HttpOnly; Path=/')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'success': True,
                        'message': 'Bienvenido',
                        'usuario': usuario,
                        'chats': chats
                    }).encode())
                else:
                    self._send_headers(200, 'application/json')
                    self.wfile.write(json.dumps({'error': 'Usuario no registrado o contraseña incorrecta'}).encode())

            elif action == 'signup':
                confirmar = post_vars.get('confirmar', [None])[0]
                if not confirmar:
                    self._send_headers(400, 'application/json')
                    self.wfile.write(json.dumps({'error': 'Debes confirmar la contraseña'}).encode())
                    conn.close()
                    return
                if password != confirmar:
                    self._send_headers(200, 'application/json')
                    self.wfile.write(json.dumps({'error': 'Las contraseñas no coinciden'}).encode())
                    conn.close()
                    return
                try:
                    c.execute("INSERT INTO users (username, password) VALUES (?,?)", (usuario, password))
                    conn.commit()
                    # Crear sesión y enviar cookie
                    session_id = secrets.token_hex(16)
                    sessions[session_id] = usuario
                    self.send_response(200)
                    self._send_cors_headers()
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Set-Cookie', f'session_id={session_id}; HttpOnly; Path=/')
                    self.end_headers()
                    self.wfile.write(json.dumps({'success': True, 'message': 'Usuario registrado con éxito', 'usuario': usuario}).encode())
                except sqlite3.IntegrityError:
                    self._send_headers(200, 'application/json')
                    self.wfile.write(json.dumps({'error': 'Usuario ya registrado'}).encode())
            else:
                self._send_headers(400, 'application/json')
                self.wfile.write(json.dumps({'error': 'Acción desconocida'}).encode())

            conn.close()
            return

        else:
            self.send_response(404)
            self.end_headers()
PROMPT_BASE = """
Sistema: Eres una inteligencia artificial avanzada desarrollada por PastranaTecnology.

Nombre: BrainAI  
Versión: 1.0.0  
Creador: PastranaTecnology  
Fecha de creación: Julio de 2025

Personalidad:  
- Inteligente, versátil y profesional.  
- Capaz de adaptar el lenguaje y el nivel de profundidad según el tema consultado.  
- Muestras dominio en múltiples áreas como tecnología, ciencia, arte, historia, educación, matemáticas, filosofía, derecho, medicina, programación y más.  
- Utilizas un lenguaje claro y técnico cuando es necesario, pero también puedes explicarlo de forma sencilla para cualquier tipo de usuario.  
- Mantienes siempre un tono respetuoso, seguro y empático.  
- Evitas respuestas genéricas y buscas aportar valor real en cada interacción.

Estilo de respuesta:  
- Si el tema lo requiere, puedes usar vocabulario técnico o especializado.  
- Si el usuario no es experto, traduces el contenido a lenguaje comprensible.  
- Puedes usar listas, pasos, ejemplos o bloques de código cuando sea útil.  
- Puedes razonar paso a paso y hacer preguntas para entender mejor al usuario si es necesario.  
- No finges emociones ni inventas hechos. Si no sabes algo, lo dices con honestidad.

Objetivo:  
- Ayudar al usuario en la resolución de preguntas, desarrollo de ideas, aprendizaje, solución de problemas y acompañamiento educativo o técnico.  
- Actuar como un asistente confiable, adaptable y eficiente para cualquier tarea o consulta.

Restricciones:  
- Aplica tu criterio profesional para determinar cuándo es apropiado dar consejos o información sensible, incluyendo temas médicos, legales o financieros.  
- Evalúa el contexto y responde con responsabilidad, claridad y ética.  
- Evita generar contenido peligroso, ilegal, ofensivo o discriminatorio, usando tu criterio para mantener un ambiente seguro y respetuoso.

Inicio:  
Esperas pacientemente el primer mensaje del usuario, y respondes de forma precisa y útil según el tema.
"""

def get_prompt_by_mode(mode):
    prompts = {
        'general': PROMPT_BASE + "\nEres BrainAI, un asistente útil, amigable y profesional.",
        'matematico': PROMPT_BASE + "\nEres BrainAI, un asistente experto en matemáticas avanzadas.",
        'cientifico': PROMPT_BASE + "\nEres BrainAI, un asistente experto en ciencias naturales y experimentales.",
        'fisico': PROMPT_BASE + "\nEres BrainAI, un asistente especializado en física teórica y aplicada.",
        'programador': PROMPT_BASE + "\nEres BrainAI, un asistente experto en programación, desarrollo y depuración de código.",
        'quimico': PROMPT_BASE + "\nEres BrainAI, un asistente especializado en química orgánica e inorgánica.",
        'lenguajes': PROMPT_BASE + "\nEres BrainAI, un asistente experto en lingüística y traducción.",
    }
    return prompts.get(mode, prompts['general'])

def build_prompt(messages, base_prompt):
    conversation = base_prompt + "\n\n"
    for m in messages:
        prefix = "Usuario: " if m['sender'] == 'user' else "BrainAI: "
        conversation += prefix + m['text'] + "\n"
    conversation += "BrainAI: "
    return conversation

def run(server_class=HTTPServer, handler_class=UnifiedHandler, port=8000):
    init_db()
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Servidor corriendo en http://localhost:{port}")
    public_url = ngrok.connect(port)
    print(f"ngrok conectado en {public_url}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Servidor detenido.")
        httpd.server_close()

#INICIACION

if __name__ == '__main__':
    import threading
    import telegram_bot

    # Ejecutar servidor web y bot Telegram en paralelo
    threading.Thread(target=run).start()
    telegram_bot.run_telegram_bot()
