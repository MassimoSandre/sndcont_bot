# bot/app.py
import os
import asyncio
import logging
from docker import DockerClient
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# Config
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")  # imposta come secret
ALLOWED_USERS = os.environ.get("ALLOWED_USERS", "")  # lista di chat_id separati da virgola (es: "12345,67890")
UPDATE_INTERVAL = int(os.environ.get("UPDATE_INTERVAL", "300"))  # secondi, default 5 min

# Set logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("docker-telegram-bot")

# Docker client (usa socket di default)
docker = DockerClient(base_url="unix://var/run/docker.sock")

def user_allowed(chat_id: int) -> bool:
    if not ALLOWED_USERS:
        return True
    allowed = [int(x.strip()) for x in ALLOWED_USERS.split(",") if x.strip()]
    return chat_id in allowed

def format_container_info(c) -> str:
    # c is a docker.models.containers.Container object
    name = ",".join(c.attrs.get("Name", "").lstrip("/").split("/")) if c.attrs.get("Name") else (c.name if hasattr(c,'name') else "")
    status = c.status
    image = c.attrs.get("Config", {}).get("Image", "")
    short_id = c.short_id if hasattr(c, "short_id") else c.id[:12]
    return f"{name} ({short_id}) — {image} — {status}"

async def list_containers_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_allowed(update.effective_chat.id):
        await update.message.reply_text("Utente non autorizzato.")
        return
    containers = docker.containers.list(all=True)
    if not containers:
        await update.message.reply_text("Nessun container trovato.")
        return
    lines = [format_container_info(c) for c in containers]
    await update.message.reply_text("Container:\n" + "\n".join(lines))

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_allowed(update.effective_chat.id):
        await update.message.reply_text("Utente non autorizzato.")
        return
    # restituisce un riassunto veloce
    running = docker.containers.list()
    total = len(docker.containers.list(all=True))
    await update.message.reply_text(f"Container totali: {total}\nIn esecuzione: {len(running)}")

async def restart_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_allowed(update.effective_chat.id):
        await update.message.reply_text("Utente non autorizzato.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /restart <container_name_or_id>")
        return
    name = context.args[0]
    try:
        c = docker.containers.get(name)
        await update.message.reply_text(f"Riavvio {name}...")
        c.restart()
        await update.message.reply_text("Riavviato.")
    except Exception as e:
        await update.message.reply_text(f"Errore: {e}")

async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_allowed(update.effective_chat.id):
        await update.message.reply_text("Utente non autorizzato.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /stop <container_name_or_id>")
        return
    name = context.args[0]
    try:
        c = docker.containers.get(name)
        c.stop()
        await update.message.reply_text("Fermato.")
    except Exception as e:
        await update.message.reply_text(f"Errore: {e}")

async def periodic_report(bot: Bot):
    """
    Funzione che manda report periodici agli utenti ALLOWED_USERS o a una CHAT_ID singola.
    """
    if not ALLOWED_USERS:
        return
    allowed = [int(x.strip()) for x in ALLOWED_USERS.split(",") if x.strip()]
    while True:
        try:
            containers = docker.containers.list(all=True)
            lines = [format_container_info(c) for c in containers]
            text = "Report container:\n" + ("\n".join(lines) if lines else "Nessun container.")
            for chat in allowed:
                await bot.send_message(chat_id=chat, text=text)
        except Exception as e:
            log.exception("Errore nel report periodico: %s", e)
        await asyncio.sleep(UPDATE_INTERVAL)

async def start_bot(polling: bool = True):
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("list", list_containers_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("restart", restart_cmd))
    app.add_handler(CommandHandler("stop", stop_cmd))

    # start periodic reporter as background task
    bot = app.bot
    app.create_task(periodic_report(bot))

    if polling:
        await app.run_polling()
    else:
        # per webhook: lancia l'applicazione in webhook mode (richiede setup esterno)
        await app.initialize()
        # webhook setup handled outside this script, see docs if you want webhooks
        await app.start()
        await app.updater.start_polling()  # fallback

if __name__ == "__main__":
    if not TELEGRAM_TOKEN:
        raise SystemExit("Set TELEGRAM_TOKEN env var")
    # usa polling per semplicità (in prod meglio webhook)
    asyncio.run(start_bot(polling=True))
