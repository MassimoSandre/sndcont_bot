import asyncio
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ALLOWED_USERS = os.environ.get("ALLOWED_USERS", "").split(",")

# --- Comandi ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("Non sei autorizzato.")
        return
    await update.message.reply_text("Ciao! Bot attivo e funzionante.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start - Avvia il bot\n/help - Mostra questo messaggio")

# --- Task periodica ---
async def periodic_report(app: "Application"):
    while True:
        for user_id in ALLOWED_USERS:
            try:
                await app.bot.send_message(chat_id=int(user_id), text="Report periodico: tutto ok ✅")
            except Exception as e:
                print(f"Errore nell'invio al {user_id}: {e}")
        await asyncio.sleep(60)

# --- Callback post start ---
async def on_startup(app: "Application"):
    # Crea la task periodica **dopo che l'event loop è attivo**
    asyncio.create_task(periodic_report(app))

# --- Main ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Registra il callback post-startup
    app.post_init(on_startup)

    # Avvia il bot (gestisce l'event loop internamente)
    app.run_polling()

if __name__ == "__main__":
    main()
