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

        # Sirve index.html o registro.html según ruta
        if self.path in ['/', '/index.html']:
            filepath = os.path.join(BASE_DIR, 'index.html')
        elif self.path == '/registro.html':
            filepath = os.path.join(BASE_DIR, 'registro.html')
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

            self.send_response(200)
            self._send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"message": answer}).encode('utf-8'))
            return

        elif self.path == '/api/title':
            data = json.loads(post_data)
            messages = data.get('messages', [])
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
                    self.send_response(200)
                    self._send_cors_headers()
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Set-Cookie', f'session_id={session_id}; HttpOnly; Path=/')
                    self.end_headers()
                    self.wfile.write(json.dumps({'success': True, 'message': 'Bienvenido', 'usuario': usuario}).encode())
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

def get_prompt_by_mode(mode):
    prompts = {
        'general': "Eres BrainAI, un asistente útil, amigable y profesional.",
        'matematico': "Eres BrainAI, un asistente experto en matemáticas avanzadas.",
        'cientifico': "Eres BrainAI, un asistente experto en ciencias naturales y experimentales.",
        'fisico': "Eres BrainAI, un asistente especializado en física teórica y aplicada.",
        'programador': "Eres BrainAI, un asistente experto en programación, desarrollo y depuración de código.",
        'quimico': "Eres BrainAI, un asistente especializado en química orgánica e inorgánica.",
        'lenguajes': "Eres BrainAI, un asistente experto en lingüística y traducción.",
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

if __name__ == '__main__':
    run()
