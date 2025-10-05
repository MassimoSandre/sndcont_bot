import asyncio
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Token e utenti autorizzati dal container (variabili d'ambiente)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ALLOWED_USERS = os.environ.get("ALLOWED_USERS", "").split(",")

# --- Funzioni helper ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("Non sei autorizzato.")
        return
    await update.message.reply_text("Ciao! Bot attivo e funzionante.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start - Avvia il bot\n/help - Mostra questo messaggio")

# --- Task periodiche ---
async def periodic_report(app: "Application"):
    while True:
        # Esempio: invia un messaggio a tutti gli utenti autorizzati ogni 60 secondi
        for user_id in ALLOWED_USERS:
            try:
                await app.bot.send_message(chat_id=int(user_id), text="Report periodico: tutto ok ✅")
            except Exception as e:
                print(f"Errore nell'invio al {user_id}: {e}")
        await asyncio.sleep(60)  # intervallo in secondi

# --- Main ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Handler comandi
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Avvio task periodica dopo il setup del bot
    app.create_task(periodic_report(app))

    # Avvia il bot in polling (gestisce l'event loop internamente)
    app.run_polling()

if __name__ == "__main__":
    main()
