from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import cohere

API_KEY_COHERE = 'tEiSQlInoBfW2U1gtSgElZaNHbookFyGzLI2Vuuz'
co = cohere.Client(API_KEY_COHERE)

INDEX_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>axelxs - Chat Galáctico Interactivo</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');

  * {
    box-sizing: border-box;
  }
  body, html {
    margin: 0; padding: 0; height: 100%;
    font-family: 'Poppins', sans-serif;
    overflow: hidden;
    background: #000;
    color: #f0f0f3;
  }
  #backgroundCanvas {
    position: fixed;
    top: 0; left: 0;
    width: 100vw;
    height: 100vh;
    z-index: -1;
    background: radial-gradient(ellipse at center, #020111 0%, #191621 100%);
  }
  .container {
    position: fixed;
    inset: 0;
    background: rgba(10, 10, 25, 0.85);
    display: flex;
    flex-direction: column;
    padding: 2rem 1.5rem;
    backdrop-filter: blur(20px);
  }
  h1 {
    margin: 0 0 1rem;
    font-weight: 600;
    color: #a5b4fc;
    text-align: center;
    letter-spacing: 1.2px;
    font-size: 2.2rem;
  }
  #conversation {
    flex-grow: 1;
    overflow-y: auto;
    padding-right: 0.5rem;
    scroll-behavior: smooth;
  }
  .card {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 18px;
    padding: 1rem 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 6px 12px rgba(118, 75, 162, 0.2);
    max-width: 90%;
    word-wrap: break-word;
    font-size: 1rem;
    line-height: 1.4;
  }
  .card.user {
    background: #764ba2;
    color: white;
    align-self: flex-end;
    box-shadow: 0 8px 15px rgba(118, 75, 162, 0.6);
  }
  .card.bot {
    background: rgba(255, 255, 255, 0.12);
    color: #a5b4fc;
    align-self: flex-start;
  }
  form {
    display: flex;
    gap: 0.75rem;
    margin-top: 1rem;
  }
  input[type="text"] {
    flex: 1;
    border: none;
    border-radius: 24px;
    padding: 0.75rem 1.25rem;
    font-size: 1rem;
    box-shadow: 0 4px 12px rgba(118, 75, 162, 0.4);
    background: rgba(255, 255, 255, 0.1);
    color: #eee;
    transition: box-shadow 0.3s ease, background 0.3s ease;
  }
  input[type="text"]::placeholder {
    color: #bbb;
  }
  input[type="text"]:focus {
    outline: none;
    background: rgba(255, 255, 255, 0.25);
    box-shadow: 0 0 12px #a293f4;
  }
  button {
    background: #a293f4;
    border: none;
    border-radius: 24px;
    color: white;
    padding: 0 1.5rem;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 8px 15px rgba(162, 147, 244, 0.7);
    transition: background 0.3s ease;
  }
  button:hover {
    background: #764ba2;
    box-shadow: 0 10px 20px rgba(118, 75, 162, 0.8);
  }
  /* Scrollbar personalizado */
  #conversation::-webkit-scrollbar {
    width: 8px;
  }
  #conversation::-webkit-scrollbar-track {
    background: transparent;
  }
  #conversation::-webkit-scrollbar-thumb {
    background: #764ba2;
    border-radius: 8px;
  }
</style>
</head>
<body>
  <canvas id="backgroundCanvas"></canvas>
  <div class="container" role="main" aria-label="Conversación galáctica con Cohere AI">
    <h1>axelxs</h1>
    <div id="conversation" aria-live="polite" aria-relevant="additions">
      <div class="card bot" style="animation-delay: 0.1s;">¡Hola! Estoy aquí para ayudarte. Escribe tu mensaje abajo.</div>
    </div>
    <form id="chatForm" aria-label="Formulario de entrada de mensaje">
      <input type="text" id="userInput" autocomplete="off" placeholder="Escribe tu pregunta..." aria-required="true" />
      <button type="submit" aria-label="Enviar mensaje">Enviar</button>
    </form>
  </div>

<script>
// Fondo galáctico con plantilla de estrellas interactivas

const canvas = document.getElementById('backgroundCanvas');
const ctx = canvas.getContext('2d');
let width, height;

function resize() {
  width = window.innerWidth;
  height = window.innerHeight;
  canvas.width = width;
  canvas.height = height;
}
window.addEventListener('resize', resize);
resize();

// Estrella para plantilla

class Star {
  constructor() {
    this.x = Math.random() * width;
    this.y = Math.random() * height;
    this.radius = Math.random() * 1.5 + 0.5;
    this.baseRadius = this.radius;
    this.color = 'rgba(165,180,252,0.8)';
    this.velocity = { x: (Math.random()-0.5)*0.2, y: (Math.random()-0.5)*0.2 };
  }
  draw() {
    ctx.beginPath();
    ctx.shadowColor = this.color;
    ctx.shadowBlur = 10;
    ctx.fillStyle = this.color;
    ctx.arc(this.x, this.y, this.radius, 0, Math.PI*2);
    ctx.fill();
    ctx.shadowBlur = 0;
  }
  update(mouse) {
    // Moverse suavemente
    this.x += this.velocity.x;
    this.y += this.velocity.y;

    // Rebote en bordes
    if(this.x < 0 || this.x > width) this.velocity.x *= -1;
    if(this.y < 0 || this.y > height) this.velocity.y *= -1;

    // Interacción con mouse: si está cerca, aumenta tamaño y se aleja un poco
    if(mouse) {
      const dx = this.x - mouse.x;
      const dy = this.y - mouse.y;
      const dist = Math.sqrt(dx*dx + dy*dy);
      if(dist < 120) {
        this.radius = Math.min(this.baseRadius + 2, this.radius + 0.1);
        const angle = Math.atan2(dy, dx);
        this.x += Math.cos(angle) * 0.7;
        this.y += Math.sin(angle) * 0.7;
      } else {
        // Vuelve al tamaño base poco a poco
        if(this.radius > this.baseRadius) this.radius -= 0.05;
        else this.radius = this.baseRadius;
      }
    } else {
      if(this.radius > this.baseRadius) this.radius -= 0.05;
      else this.radius = this.baseRadius;
    }
  }
}

// Crear estrellas
const stars = [];
const numStars = 120;
for(let i=0; i<numStars; i++) stars.push(new Star());

let mouse = null;
window.addEventListener('mousemove', e => {
  mouse = { x: e.clientX, y: e.clientY };
});
window.addEventListener('mouseout', e => {
  mouse = null;
});

function connectStars() {
  const maxDistance = 100;
  ctx.strokeStyle = 'rgba(165,180,252,0.15)';
  ctx.lineWidth = 1;
  for(let i=0; i<stars.length; i++) {
    for(let j=i+1; j<stars.length; j++) {
      const dx = stars[i].x - stars[j].x;
      const dy = stars[i].y - stars[j].y;
      const dist = Math.sqrt(dx*dx + dy*dy);
      if(dist < maxDistance) {
        ctx.beginPath();
        ctx.moveTo(stars[i].x, stars[i].y);
        ctx.lineTo(stars[j].x, stars[j].y);
        ctx.stroke();
      }
    }
  }
  // Líneas al cursor
  if(mouse) {
    ctx.strokeStyle = 'rgba(255,255,255,0.2)';
    for(let star of stars) {
      const dx = star.x - mouse.x;
      const dy = star.y - mouse.y;
      const dist = Math.sqrt(dx*dx + dy*dy);
      if(dist < maxDistance) {
        ctx.beginPath();
        ctx.moveTo(star.x, star.y);
        ctx.lineTo(mouse.x, mouse.y);
        ctx.stroke();
      }
    }
  }
}

function animate(time=0) {
  ctx.clearRect(0, 0, width, height);

  // Nebulosa suave de fondo
  let grd = ctx.createRadialGradient(width/2, height/2, 50, width/2, height/2, 600);
  grd.addColorStop(0, 'rgba(118,75,162,0.6)');
  grd.addColorStop(0.4, 'rgba(166,117,255,0.2)');
  grd.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = grd;
  ctx.fillRect(0,0,width,height);

  for(let star of stars) {
    star.update(mouse);
    star.draw();
  }
  connectStars();

  requestAnimationFrame(animate);
}
animate();

// Chat funcional

const form = document.getElementById('chatForm');
const input = document.getElementById('userInput');
const conversation = document.getElementById('conversation');

function appendMessage(text, sender) {
  const card = document.createElement('div');
  card.classList.add('card', sender);
  card.textContent = text;
  conversation.appendChild(card);
  conversation.scrollTop = conversation.scrollHeight;
}

form.addEventListener('submit', async e => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;

  appendMessage(text, 'user');
  input.value = '';
  input.disabled = true;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text })
    });
    const data = await res.json();
    appendMessage(data.reply, 'bot');
  } catch {
    appendMessage('Error al conectar con el servidor.', 'bot');
  } finally {
    input.disabled = false;
    input.focus();
  }
});

input.focus();
</script>
</body>
</html>
"""

class ChatHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(INDEX_HTML.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'404 - No encontrado')

    def do_POST(self):
        if self.path == '/api/chat':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            user_message = data.get('message', '')

            if not user_message:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({'reply': 'Mensaje vacío.'}).encode('utf-8'))
                return

            try:
                response = co.generate(
                    model='command-r-plus',
                    prompt=user_message,
                    max_tokens=150
                )
                reply = response.generations[0].text.strip()
            except Exception:
                reply = 'Error al conectar con Cohere.'

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'reply': reply}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    print("Iniciando servidor en http://localhost:5000 ...")
    server_address = ('localhost', 5000)
    httpd = HTTPServer(server_address, ChatHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
