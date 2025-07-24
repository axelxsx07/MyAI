from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import cohere
from pyngrok import ngrok

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
  html, body {
    margin: 0; padding: 0;
    height: 100%;
    background: radial-gradient(circle at center, #0f0f23, #000010);
    color: #fff;
    padding-bottom: env(safe-area-inset-bottom);
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  }
  .app-container {
    display: flex;
    height: 100vh;
    position: relative;
  }
  .sidebar {
    width: 280px;
    background: rgba(20,20,35,0.95);
    border-right: 1px solid #444654;
    display: flex;
    flex-direction: column;
    position: absolute;
    left: -300px;
    top: 0;
    bottom: 0;
    transition: left 0.4s ease;
    z-index: 2;
  }
  .sidebar.open {
    left: 0;
    animation: bubbleIn 0.4s ease forwards;
  }
  .sidebar h2 {
    text-align: center;
    padding: 1rem;
    margin: 0;
    font-size: 1.2rem;
    border-bottom: 1px solid #444654;
  }
  #chatList {
    list-style: none;
    padding: 0;
    margin: 0;
    flex-grow: 1;
    overflow-y: auto;
  }
  .sidebar li {
    padding: 0.75rem 1rem;
    cursor: pointer;
    border-bottom: 1px solid #333;
    animation: slideInLi 0.3s ease;
    animation-fill-mode: both;
  }
  .sidebar li.active {
    background-color: #333;
  }
  .new-chat {
    padding: 1rem;
    text-align: center;
    background: #1e1e2e;
    border-top: 1px solid #444654;
    cursor: pointer;
    font-weight: bold;
  }
  .new-chat.animated {
    animation: bubbleIn 0.3s ease;
  }
  .sidebar .footer {
    padding: 1rem;
    text-align: center;
    font-size: 0.85rem;
    color: #aaa;
    border-top: 1px solid #444654;
  }
  .chat-area {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    height: 100vh;
    transition: margin-left 0.4s ease;
    z-index: 1;
    margin-left: 0;
  }
  .chat-area.shifted {
    margin-left: 280px;
  }
  .chat-header {
    padding: 1rem;
    background: #1a1a2f;
    display: flex;
    align-items: center;
    gap: 1rem;
    border-bottom: 1px solid #444654;
  }
  .chat-header h1 {
    font-size: 1.1rem;
    margin: 0;
  }
  #toggleSidebar {
    background: none;
    border: none;
    color: #fff;
    font-size: 1.5rem;
    cursor: pointer;
    transition: transform 0.3s;
  }
  #toggleSidebar.rotated {
    transform: rotate(90deg);
  }
  #conversation {
    flex-grow: 1;
    overflow-y: auto;
    padding: 1rem;
    padding-bottom: calc(4rem + env(safe-area-inset-bottom)); /* espacio para input fijo */
    display: flex;
    flex-direction: column;
    gap: 1rem;
    background: url("https://www.transparenttextures.com/patterns/cubes.png") repeat;
  }
  .message {
    max-width: 75%;
    padding: 1rem;
    border-radius: 20px;
    white-space: pre-wrap;
    line-height: 1.4;
    opacity: 0;
    transform: translateY(10px);
    animation: fadeIn 0.4s forwards;
  }
  .user {
    align-self: flex-end;
    background: #1e90ff;
  }
  .bot {
    align-self: flex-start;
    background: #2e2e2e;
  }
  .input-area {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    display: flex;
    padding: 1rem;
    padding-bottom: calc(1rem + env(safe-area-inset-bottom));
    border-top: 1px solid #444654;
    background: #111;
    z-index: 10;
  }
  .input-area input {
    flex-grow: 1;
    padding: 0.75rem;
    border-radius: 10px;
    border: none;
    font-size: 1rem;
    color: #fff;
    background: #222;
  }
  .input-area input::placeholder {
    color: #999;
  }
  .input-area button {
    margin-left: 1rem;
    padding: 0.75rem 1rem;
    border-radius: 10px;
    border: none;
    background: #1e90ff;
    color: #fff;
    font-weight: bold;
    cursor: pointer;
    transition: background-color 0.3s ease;
  }
  .input-area button:hover:not(:disabled) {
    background: #0a60d9;
  }
  .input-area button:disabled {
    background: #555;
    cursor: not-allowed;
  }

  /* Animación fadeIn para mensajes */
  @keyframes fadeIn {
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  /* Animación tipo burbuja */
  @keyframes bubbleIn {
    0% { transform: scale(0.6); opacity: 0; }
    60% { transform: scale(1.05); opacity: 1; }
    100% { transform: scale(1); }
  }
  /* Animación lista chats */
  @keyframes slideInLi {
    from { transform: translateX(-20px); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
  }

  /* Animación para los tres puntos tipo ChatGPT */
  .typing {
    display: flex;
    gap: 6px;
    margin-left: 10px;
    align-items: center;
  }
  .typing span {
    width: 8px;
    height: 8px;
    background: #1e90ff;
    border-radius: 50%;
    animation: blink 1.4s infinite;
    opacity: 0.3;
  }
  .typing span:nth-child(1) {
    animation-delay: 0s;
  }
  .typing span:nth-child(2) {
    animation-delay: 0.2s;
  }
  .typing span:nth-child(3) {
    animation-delay: 0.4s;
  }
  @keyframes blink {
    0%, 80%, 100% { opacity: 0.3; }
    40% { opacity: 1; }
  }
</style>
</head>
<body>
  <div class="app-container">
    <div class="sidebar" id="sidebar">
      <h2>Chats</h2>
      <ul id="chatList"></ul>
      <div class="new-chat" id="newChatBtn" onclick="newChat()">➕ Nuevo chat</div>
      <div class="footer">by: PastranaTecnology</div>
    </div>
    <div class="chat-area" id="chatArea">
      <div class="chat-header">
        <button id="toggleSidebar">☰</button>
        <h1>Asistente IA</h1>
      </div>
      <div id="conversation"></div>
      <div class="input-area">
        <input type="text" id="userInput" placeholder="Escribe tu mensaje..." autocomplete="off" />
        <button id="sendBtn" disabled>Enviar</button>
      </div>
    </div>
  </div>

<script>
  const sidebar = document.getElementById('sidebar');
  const toggleBtn = document.getElementById('toggleSidebar');
  const chatList = document.getElementById('chatList');
  const conversation = document.getElementById('conversation');
  const userInput = document.getElementById('userInput');
  const sendBtn = document.getElementById('sendBtn');
  const chatArea = document.getElementById('chatArea');

  let chats = [];
  let current = null;

  toggleBtn.onclick = () => {
    const open = sidebar.classList.toggle('open');
    toggleBtn.classList.toggle('rotated', open);
    if(open) {
      chatArea.classList.add('shifted');
    } else {
      chatArea.classList.remove('shifted');
    }
  };

  function newChat() {
    const n = { title: '', msgs: [{ text: '¡Hola! ¿Cómo puedo ayudarte?', sender: 'bot' }] };
    chats.push(n);
    select(n);
    renderList();
    sidebar.classList.remove('open');
    toggleBtn.classList.remove('rotated');
    chatArea.classList.remove('shifted');
    // Animación burbuja en botón
    const btn = document.getElementById('newChatBtn');
    btn.classList.add('animated');
    setTimeout(() => btn.classList.remove('animated'), 400);
  }

  function select(c) {
    current = c;
    render();
  }

  function renderList() {
    chatList.innerHTML = '';
    chats.forEach((c, i) => {
      const li = document.createElement('li');
      li.textContent = c.title || 'Chat ' + (i + 1);
      li.className = c === current ? 'active' : '';
      li.style.animationDelay = `${i * 0.05}s`;
      li.onclick = () => { select(c) };
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
  }

  function setTyping(on) {
    if(on) {
      const d = document.createElement('div');
      d.className = 'typing';
      d.id = 'typing';
      d.innerHTML = '<span></span><span></span><span></span>';
      conversation.appendChild(d);
      conversation.scrollTop = conversation.scrollHeight;
      sendBtn.disabled = true;
    } else {
      const t = document.getElementById('typing');
      if(t) t.remove();
      sendBtn.disabled = false;
    }
  }

  sendBtn.onclick = async () => {
    const text = userInput.value.trim();
    if(!text || !current) return;
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
        if self.path == '/api/chat':
            length = int(self.headers.get('Content-Length', 0))
            data = json.loads(self.rfile.read(length))
            msg = data.get('message', '').strip()
            history = data.get('context', [])
            if not msg:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({'reply': 'Mensaje vacío.'}).encode('utf-8'))
                return
            prompt = "\\n".join([f"{m['sender'].capitalize()}: {m['text']}" for m in history]) + "\\nIa:"
            try:
                resp = co.generate(model='command-r-plus', prompt=prompt, max_tokens=150)
                reply = resp.generations[0].text.strip()
            except Exception as e:
                reply = f"Error IA: {e}"
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'reply': reply}).encode('utf-8'))
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
        print("\n Servidor detenido.")
