# telegram_bot.py
import telebot
from server import get_prompt_by_mode, build_prompt, co

TELEGRAM_BOT_TOKEN = '7609862924:AAGsxaRvN-t5_qHN3ACpLZe5VR6MmTINXzM'
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, "👋 ¡Hola! Soy BrainAI en Telegram. Escribe tu pregunta o tema y te ayudaré.")

@bot.message_handler(func=lambda msg: True)
def chat_handler(message):
    user_input = message.text
    mode = "general"  # Puedes cambiar dinámicamente según tu lógica

    try:
        prompt_base = get_prompt_by_mode(mode)
        prompt = build_prompt([{"text": user_input, "sender": "user"}], prompt_base)

        response = co.generate(
            model='command-r-plus',
            prompt=prompt,
            max_tokens=300,
            temperature=0.7,
            k=0,
            p=0.75,
            stop_sequences=["--"],
        )
        answer = response.generations[0].text.strip()
    except Exception as e:
        answer = f"❌ Error al generar respuesta: {str(e)}"

    bot.reply_to(message, answer)

def run_telegram_bot():
    print("🤖 Bot de Telegram iniciado...")
    bot.infinity_polling()
