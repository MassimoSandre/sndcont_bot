import asyncio
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ALLOWED_USERS = os.environ.get("ALLOWED_USERS", "").split(",")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("Non sei autorizzato.")
        return
    await update.message.reply_text("Ciao! Bot attivo e funzionante.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start - Avvia il bot\n/help - Mostra questo messaggio")

async def periodic_report(app: "ApplicationBuilder"):
    while True:
        for user_id in ALLOWED_USERS:
            try:
                await app.bot.send_message(chat_id=int(user_id), text="Report periodico: tutto ok ✅")
            except Exception as e:
                print(f"Errore nell'invio al {user_id}: {e}")
        await asyncio.sleep(60)

async def main_async():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Avvia la periodic task subito dopo la creazione dell'app
    app.create_task(periodic_report(app))

    # Avvia il bot
    await app.run_polling()

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
