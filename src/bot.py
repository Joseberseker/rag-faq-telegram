"""Adaptador de Telegram: recibe mensajes por long-polling (sin webhook, sin
servidor público) y los resuelve contra el mismo núcleo de rag.py/memory.py
que usa el widget web."""

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from . import config, memory, rag
from .llm_client import OllamaClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_llm = OllamaClient()

WELCOME_MESSAGE = (
    "¡Hola! Soy el asistente de soporte de NovaShop. "
    "Pregúntame sobre envíos, devoluciones, pagos o el estado de tu pedido."
)


async def start(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME_MESSAGE)


async def handle_message(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    question = update.message.text

    history = memory.get_history(chat_id)
    result = rag.answer(question, history=history, llm=_llm)

    memory.append_turn(chat_id, "user", question)
    memory.append_turn(chat_id, "assistant", result.text)

    reply = result.text
    if result.sources:
        reply += "\n\n📎 Fuente: " + ", ".join(result.sources)

    await update.message.reply_text(reply)


def build_application() -> Application:
    if not config.TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "Falta TELEGRAM_BOT_TOKEN en el entorno — definelo en tu .env (ver .env.example)."
        )

    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return application


def main() -> None:
    application = build_application()
    logger.info("Bot de Telegram iniciado (polling)...")
    application.run_polling()


if __name__ == "__main__":
    main()
