# app.py
import os
import asyncio
from typing import List, Optional

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# opzionali: pip install docker
# usalo se vuoi che il bot legga lo stato dei container
try:
    from docker import DockerClient
except Exception:
    DockerClient = None

# Config
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ALLOWED_USERS_ENV = os.environ.get("ALLOWED_USERS", "")  # "12345,67890"
UPDATE_INTERVAL = int(os.environ.get("UPDATE_INTERVAL", "300"))  # secondi

if not TELEGRAM_TOKEN:
    raise SystemExit("Set TELEGRAM_TOKEN environment variable")

def parse_allowed_users(env: str) -> List[int]:
    out = []
    for part in env.split(","):
        s = part.strip()
        if not s:
            continue
        try:
            out.append(int(s))
        except ValueError:
            # ignora valori non numerici
            pass
    return out

ALLOWED_USERS = parse_allowed_users(ALLOWED_USERS_ENV)

def user_is_allowed(chat_id: int) -> bool:
    if not ALLOWED_USERS:
        return True  # nessuna lista = aperto a tutti (cambia se vuoi)
    return chat_id in ALLOWED_USERS

def get_docker_client() -> Optional["DockerClient"]:
    if DockerClient is None:
        return None
    try:
        # crea il client al volo (evita errori in import)
        return DockerClient(base_url="unix://var/run/docker.sock")
    except Exception:
        return None

def format_container_info(c) -> str:
    try:
        name = (c.name if hasattr(c, "name") else c.attrs.get("Name", "").lstrip("/"))
        short_id = c.short_id if hasattr(c, "short_id") else (c.id[:12] if hasattr(c, "id") else "")
        image = c.attrs.get("Config", {}).get("Image", "") if hasattr(c, "attrs") else ""
        status = getattr(c, "status", "unknown")
        return f"{name} ({short_id}) — {image} — {status}"
    except Exception:
        return "<err>"

# --- Handlers ---
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_is_allowed(update.effective_chat.id):
        await update.message.reply_text("Utente non autorizzato.")
        return
    await update.message.reply_text("Bot attivo. Usa /list o /status")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/list - elenca container\n/status - riepilogo\n/restart <name> - riavvia container\n/stop <name> - ferma container")

async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_is_allowed(update.effective_chat.id):
        await update.message.reply_text("Utente non autorizzato.")
        return
    client = get_docker_client()
    if client is None:
        await update.message.reply_text("Docker SDK non disponibile o non accessibile.")
        return
    try:
        containers = client.containers.list(all=True)
        if not containers:
            await update.message.reply_text("Nessun container trovato.")
            return
        text = "\n".join(format_container_info(c) for c in containers)
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"Errore leggendo Docker: {e}")

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_is_allowed(update.effective_chat.id):
        await update.message.reply_text("Utente non autorizzato.")
        return
    client = get_docker_client()
    if client is None:
        await update.message.reply_text("Docker SDK non disponibile o non accessibile.")
        return
    try:
        running = client.containers.list()
        total = len(client.containers.list(all=True))
        await update.message.reply_text(f"Container totali: {total}\nIn esecuzione: {len(running)}")
    except Exception as e:
        await update.message.reply_text(f"Errore: {e}")

async def cmd_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_is_allowed(update.effective_chat.id):
        await update.message.reply_text("Utente non autorizzato.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /restart <container_name_or_id>")
        return
    name = context.args[0]
    client = get_docker_client()
    if client is None:
        await update.message.reply_text("Docker non accessibile.")
        return
    try:
        c = client.containers.get(name)
        c.restart()
        await update.message.reply_text(f"{name} riavviato.")
    except Exception as e:
        await update.message.reply_text(f"Errore: {e}")

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_is_allowed(update.effective_chat.id):
        await update.message.reply_text("Utente non autorizzato.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /stop <container_name_or_id>")
        return
    name = context.args[0]
    client = get_docker_client()
    if client is None:
        await update.message.reply_text("Docker non accessibile.")
        return
    try:
        c = client.containers.get(name)
        c.stop()
        await update.message.reply_text(f"{name} fermato.")
    except Exception as e:
        await update.message.reply_text(f"Errore: {e}")

# --- Job (periodic report) ---
async def job_report(context: ContextTypes.DEFAULT_TYPE):
    """job callback eseguito dal JobQueue"""
    client = get_docker_client()
    if client is None:
        text = "Docker non disponibile / permessi mancanti"
    else:
        try:
            containers = client.containers.list(all=True)
            lines = [format_container_info(c) for c in containers] or ["Nessun container"]
            text = "Report container:\n" + "\n".join(lines)
        except Exception as e:
            text = f"Errore nel report Docker: {e}"

    # invia a tutti gli allowed users
    for uid in ALLOWED_USERS:
        try:
            await context.bot.send_message(chat_id=int(uid), text=text)
        except Exception:
            # ignora errori di invio individuale
            pass

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # registra comandi
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("restart", cmd_restart))
    app.add_handler(CommandHandler("stop", cmd_stop))

    # schedule job periodico tramite il JobQueue (prima di run_polling va bene)
    # first=10: aspetta 10 secondi al primo run per permettere startup
    app.job_queue.run_repeating(job_report, interval=UPDATE_INTERVAL, first=10)

    # avvia il bot (blocking call, gestisce event loop internamente)
    app.run_polling()

if __name__ == "__main__":
    main()
