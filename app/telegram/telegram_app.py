from __future__ import annotations

from io import BytesIO
from typing import Any

from fastapi import FastAPI
from telegram import InputFile, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from app.config.settings import get_settings
from app.database.database import SessionLocal, init_db
from app.seed import seed_demo_data
from app.telegram.handlers import TelegramHandler


def _parse_authorized_ids(raw: str | None) -> set[int]:
    if not raw:
        return set()
    return {int(part.strip()) for part in raw.split(',') if part.strip()}


def _format_response(payload: dict[str, Any]) -> str:
    summary = str(payload.get('summary') or 'I processed your request.')
    action = str(payload.get('action') or 'request')
    if action == 'stock':
        return summary
    if action == 'bill':
        return summary
    return summary


async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings()
    user = update.effective_user
    if user is None:
        return
    authorized = _parse_authorized_ids(settings.authorized_telegram_user_ids)
    if authorized and user.id not in authorized:
        await update.message.reply_text('You are not authorized to use this Nebula store bot.')
        return
    await update.message.reply_text(
        'Welcome to Nebula KnowLab Store Agent.\n\n'
        'Commands:\n'
        '/start - welcome\n'
        '/help - capability list\n'
        '/status - store snapshot\n'
        '/new - start fresh conversation\n'
        '/cancel - cancel current workflow\n\n'
        'You can also send natural-language requests like: "How much Maggi left?" or "Create a draft bill".'
    )


async def _help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'Nebula capabilities:\n'
        '- Inventory: stock checks, receive stock, low-stock alerts\n'
        '- Billing: create/edit/finalize draft bills\n'
        '- Khata: customer credit and payment tracking\n'
        '- Analytics: daily and sales summaries\n'
        '- Documents: PDF invoices and PPTX sales decks'
    )


async def _new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None or update.message is None:
        return
    db = SessionLocal()
    try:
        session_id = TelegramHandler(db).new_session(user.id)
        await update.message.reply_text(
            f'Fresh Nebula conversation started (session {session_id}). Your store data remains available.'
        )
    finally:
        db.close()


async def _status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None or update.message is None:
        return
    db = SessionLocal()
    try:
        handler = TelegramHandler(db)
        result = handler.process('What can you do?', user_id=user.id)
        await update.message.reply_text(_format_response(result))
    finally:
        db.close()


async def _cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Current workflow cancelled. You can continue with a new request.')


async def _message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings()
    user = update.effective_user
    if user is None:
        return
    authorized = _parse_authorized_ids(settings.authorized_telegram_user_ids)
    if authorized and user.id not in authorized:
        await update.message.reply_text('You are not authorized to use this Nebula store bot.')
        return
    text = update.message.text or ''
    if not text.strip():
        return
    db = SessionLocal()
    try:
        handler = TelegramHandler(db)
        result = handler.process(text, user_id=user.id)
        invoice_pdf = result.get('invoice_pdf')
        if invoice_pdf:
            await update.message.reply_document(
                document=InputFile(BytesIO(invoice_pdf), filename=result.get('invoice_filename', 'invoice.pdf')),
                caption=_format_response(result),
            )
        else:
            await update.message.reply_text(_format_response(result))
    finally:
        db.close()


def setup_telegram_app(app: FastAPI) -> None:
    settings = get_settings()
    token = settings.telegram_bot_token
    if not token:
        return

    init_db()
    seed_demo_data()

    application = ApplicationBuilder().token(token).build()
    application.add_handler(CommandHandler('start', _start))
    application.add_handler(CommandHandler('help', _help))
    application.add_handler(CommandHandler('new', _new))
    application.add_handler(CommandHandler('status', _status))
    application.add_handler(CommandHandler('cancel', _cancel))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _message))

    app.state.telegram_application = application

    @app.on_event('startup')
    async def startup_event() -> None:
        await application.initialize()
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)

    @app.on_event('shutdown')
    async def shutdown_event() -> None:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
