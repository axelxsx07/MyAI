from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import cohere
from pyngrok import ngrok

# Configuración ngrok y Cohere
ngrok.set_auth_token("30IUO0tKAb6INPbCEIRBCj9N4fW_46F1JyMvuoUw8ik1pDefC")
API_KEY_COHERE = 'tEiSQlInoBfW2U1gtSgElZaNHbookFyGzLI2Vuuz'
co = cohere.Client(API_KEY_COHERE)

INDEX_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<title>Chat IA - PastranaTechnology</title>
<style>
  html, body { margin: 0; padding: 0; height: 100%;
    background: radial-gradient(circle at center, #0f0f23, #000010);
    color: #fff; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    padding-bottom: env(safe-area-inset-bottom);
  }
  .app-container { display: flex; height: 100vh; position: relative; }
  .sidebar {
    width: 280px; background: rgba(20,20,35,0.95);
    border-right: 1px solid #444654;
    position: absolute; left: -300px; top: 0; bottom: 0;
    display: flex; flex-direction: column;
    transition: left 0.4s ease; z-index: 2;
  }
  .sidebar.open { left: 0; animation: bubbleIn 0.4s ease forwards; }
  
  /* Encabezado sidebar con logo */
  .sidebar h2 {
    text-align: center; padding: 1rem; margin: 0;
    font-size: 1.2rem; border-bottom: 1px solid #444654;
  }
  .sidebar h2 img.header-logo {
    height: 1em;
    vertical-align: middle;
    margin-right: 0.4em;
    border-radius: 4px;
  }

  #chatList { list-style: none; padding: 0; margin: 0;
    flex-grow: 1; overflow-y: auto;
  }
  .sidebar li {
    padding: 0.75rem 1rem; cursor: pointer;
    border-bottom: 1px solid #333;
    animation: slideInLi 0.3s ease both;
  }
  .sidebar li.active { 
    background-color: #333; 
    border-left: 4px solid #1e90ff;
    padding-left: calc(1rem - 4px);
  }
  .new-chat {
    padding: 1rem; text-align: center; background: #1e1e2e;
    border-top: 1px solid #444654; cursor: pointer; font-weight: bold;
  }
  .new-chat.animated { animation: bubbleIn 0.3s ease; }
  
  /* Footer con logo */
  .sidebar .footer {
    padding: 1rem; text-align: center; font-size: 0.85rem;
    color: #aaa; border-top: 1px solid #444654;
  }
  .footer img.footer-logo {
    height: 1em;
    vertical-align: middle;
    margin: 0 0.3em;
    border-radius: 4px;
  }

  .chat-area {
    flex-grow: 1; display: flex; flex-direction: column;
    height: 100vh; transition: margin-left 0.4s ease; margin-left: 0; z-index: 1;
  }
  .chat-area.shifted { margin-left: 280px; }
  .chat-header {
    padding: 1rem; background: #1a1a2f;
    display: flex; align-items: center; gap: 1rem;
    border-bottom: 1px solid #444654;
  }
  .chat-header h1 { font-size: 1.1rem; margin: 0; }
  #chatTitle { font-size: 0.95rem; margin-left: 1rem; color: #aaa; }
  #toggleSidebar {
    background: none; border: none; color: #fff;
    font-size: 1.5rem; cursor: pointer;
    transition: transform 0.3s;
  }
  #toggleSidebar.rotated { transform: rotate(90deg); }
  #conversation {
    flex-grow: 1; overflow-y: auto; padding: 1rem;
    padding-bottom: calc(4rem + env(safe-area-inset-bottom));
    display: flex; flex-direction: column; gap: 1rem;
    background: url("https://www.transparenttextures.com/patterns/cubes.png") repeat;
  }
  .message {
    max-width: 75%; padding: 1rem; border-radius: 20px;
    white-space: pre-wrap; line-height: 1.4;
    opacity: 0; transform: translateY(10px);
    animation: fadeIn 0.4s forwards;
  }
  .user { align-self: flex-end; background: #1e90ff; }
  .bot  { align-self: flex-start; background: #2e2e2e; }
  .input-area {
    position: fixed; bottom: 0; left: 0; right: 0;
    display: flex; padding: 1rem;
    padding-bottom: calc(1rem + env(safe-area-inset-bottom));
    border-top: 1px solid #444654; background: #111; z-index: 10;
    transition: left 0.4s ease;
  }
  .input-area.shifted { left: 280px; animation: bubbleIn 0.4s ease forwards; }
  .input-area input {
    flex-grow: 1; padding: 0.75rem; border-radius: 10px;
    border: none; font-size: 1rem; background: #222; color: #fff;
  }
  .input-area input::placeholder { color: #999; }
  .input-area button {
    margin-left: 1rem; padding: 0.75rem 1rem; border-radius: 10px;
    border: none; font-weight: bold; cursor: pointer;
    background: #1e90ff; color: #fff;
    transition: background-color 0.3s ease;
  }
  .input-area button:hover:not(:disabled) { background: #0a60d9; }
  .input-area button:disabled { background: #555; cursor: not-allowed; }
  @keyframes fadeIn { to { opacity: 1; transform: translateY(0); } }
  @keyframes bubbleIn {
    0% { transform: scale(0.6); opacity: 0; }
    60% { transform: scale(1.05); opacity: 1; }
    100% { transform: scale(1); }
  }
  @keyframes slideInLi {
    from { transform: translateX(-20px); opacity: 0; }
    to   { transform: translateX(0);  opacity: 1; }
  }
  .typing {
    display: flex; gap: 6px; margin-left: 10px; align-items: center;
  }
  .typing span {
    width: 8px; height: 8px; background: #1e90ff;
    border-radius: 50%; animation: blink 1.4s infinite; opacity: 0.3;
  }
  .typing span:nth-child(1) { animation-delay: 0s; }
  .typing span:nth-child(2) { animation-delay: 0.2s; }
  .typing span:nth-child(3) { animation-delay: 0.4s; }
  @keyframes blink {
    0%,80%,100% { opacity: 0.3; }
    40%         { opacity: 1;   }
  }
</style>
</head>
<body>
  <div class="app-container">
    <div class="sidebar" id="sidebar">
      <h2>
        <img src="https://raw.githubusercontent.com/axelxsx07/logo/main/2347FCDD-F04C-4C09-87F9-66069E2367B8.png" alt="logo" class="header-logo" />
        CHATS
      </h2>
      <ul id="chatList"></ul>
      <div class="new-chat" id="newChatBtn" onclick="newChat()">➕ Nuevo chat</div>
      <div class="footer">
        by: <img src="https://raw.githubusercontent.com/axelxsx07/logo/main/2347FCDD-F04C-4C09-87F9-66069E2367B8.png" alt="logo" class="footer-logo" /> PastranaTecnology
      </div>
    </div>
    <div class="chat-area" id="chatArea">
      <div class="chat-header">
        <button id="toggleSidebar">☰</button>
        <h1>Asistente IA</h1>
        <span id="chatTitle"></span>
      </div>
      <div id="conversation"></div>
      <div class="input-area">
        <input type="text" id="userInput" placeholder="Escribe tu mensaje..." autocomplete="off" />
        <button id="sendBtn" disabled>Enviar</button>
      </div>
    </div>
  </div>

<script>
  const sidebar    = document.getElementById('sidebar');
  const toggleBtn  = document.getElementById('toggleSidebar');
  const chatList   = document.getElementById('chatList');
  const conversation = document.getElementById('conversation');
  const userInput  = document.getElementById('userInput');
  const sendBtn    = document.getElementById('sendBtn');
  const chatArea   = document.getElementById('chatArea');

  let chats = [];
  let current = null;

  toggleBtn.onclick = () => {
    const open = sidebar.classList.toggle('open');
    toggleBtn.classList.toggle('rotated', open);
    chatArea.classList.toggle('shifted', open);
    document.querySelector('.input-area').classList.toggle('shifted', open);
  };

  async function generateTitle(chat) {
    try {
      const firstUserMessage = chat.msgs.find(m => m.sender === 'user');
      if (!firstUserMessage) return;

      const res = await fetch('/api/title', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: [firstUserMessage] })
      });
      const data = await res.json();
      if (!chat.title) {
        chat.title = data.title || '';
        console.log('Título generado:', chat.title);
        renderList();
        render();
      }
    } catch (e) {
      console.error('Error generando título:', e);
    }
  }

  function newChat() {
    const n = { title: '', msgs: [{ text: '¡Hola! ¿Cómo puedo ayudarte?', sender: 'bot' }] };
    chats.push(n);
    select(n);
    renderList();
    sidebar.classList.remove('open');
    toggleBtn.classList.remove('rotated');
    chatArea.classList.remove('shifted');
    document.querySelector('.input-area').classList.remove('shifted');
    const btn = document.getElementById('newChatBtn');
    btn.classList.add('animated');
    setTimeout(() => btn.classList.remove('animated'), 400);
  }

  function select(c) {
    current = c;
    render();
    renderList();
  }

  function renderList() {
    chatList.innerHTML = '';
    chats.forEach((c, i) => {
      const li = document.createElement('li');
      const nro = i + 1;
      li.textContent = c.title
        ? `Chat ${nro} - ${c.title}`
        : `Chat ${nro}`;
      li.className = '';
      if (c === current) li.classList.add('active');
      li.style.animationDelay = `${i * 0.05}s`;
      li.onclick = () => select(c);
      chatList.appendChild(li);
    });
  }

  function render() {
    conversation.innerHTML = '';
    current.msgs.forEach(m => {
      const div = document.createElement('div');
      div.className = 'message ' + m.sender;
      div.textContent = m.text;
      conversation.appendChild(div);
    });
    conversation.scrollTop = conversation.scrollHeight;
    sendBtn.disabled = false;
    const idx = chats.indexOf(current) + 1;
    document.getElementById('chatTitle').textContent =
      current.title || `Chat ${idx}`;
  }

  function setTyping(on) {
    if (on) {
      const d = document.createElement('div');
      d.className = 'typing';
      d.id = 'typing';
      d.innerHTML = '<span></span><span></span><span></span>';
      conversation.appendChild(d);
      conversation.scrollTop = conversation.scrollHeight;
      sendBtn.disabled = true;
    } else {
      const t = document.getElementById('typing');
      if (t) t.remove();
      sendBtn.disabled = false;
    }
  }

  sendBtn.onclick = async () => {
    const text = userInput.value.trim();
    if (!text || !current) return;
    current.msgs.push({ text, sender: 'user' });
    userInput.value = '';
    render();
    setTyping(true);
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, context: current.msgs })
      });
      const data = await res.json();
      setTyping(false);
      current.msgs.push({ text: data.reply, sender: 'bot' });
      render();

      // Generar título solo si no existe y solo en el primer mensaje enviado por el usuario
      if (!current.title) {
        await generateTitle(current);
      }
    } catch {
      setTyping(false);
      current.msgs.push({ text: 'Error al conectar con el servidor.', sender: 'bot' });
      render();
    }
  };

  userInput.addEventListener('input', () => {
    sendBtn.disabled = userInput.value.trim().length === 0;
  });

  newChat();
</script>
</body>
</html>
"""

class ChatHandler(BaseHTTPRequestHandler):
    def _send_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(INDEX_HTML.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(length)
        if self.path == '/api/chat':
            data = json.loads(post_data)
            msg = data.get('message', '').strip()
            history = data.get('context', [])
            if not msg:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({'reply': 'Mensaje vacío.'}).encode('utf-8'))
                return
            prompt = "\n".join([f"{m['sender'].capitalize()}: {m['text']}" for m in history]) + "\nIa:"
            try:
                resp = co.generate(model='command-r-plus', prompt=prompt, max_tokens=150)
                reply = resp.generations[0].text.strip()
            except Exception as e:
                reply = f"Error IA: {e}"
            self._send_json({'reply': reply})

        elif self.path == '/api/title':
            data = json.loads(post_data)
            mensajes = data.get('messages', [])
            texto = "\n".join([f"{m['sender']}: {m['text']}" for m in mensajes[:5]])
            prompt = f'''Actúa como un asistente que genera títulos breves para chats.
Dado el inicio de la conversación, genera un título muy corto (1 a 4 palabras) y claro, sin puntuación ni comillas.

Conversación:
{texto}

Título:'''
            try:
                resp = co.generate(model='command-r-plus', prompt=prompt, max_tokens=10, temperature=0.7)
                titulo = resp.generations[0].text.strip()
            except Exception as e:
                titulo = ''
            self._send_json({'title': titulo})

        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    port = 5000
    url = ngrok.connect(port)
    print(f"Tu IA está en {url}")
    server = HTTPServer(('localhost', port), ChatHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
