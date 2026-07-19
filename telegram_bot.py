#!/usr/bin/env python3
import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from database import get_unnotified_articles, mark_notified, log_interaction

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def format_digest():
    tier1 = get_unnotified_articles(tier=1, limit=5)
    tier2 = get_unnotified_articles(tier=2, limit=10)
    
    lines = [f'🦅 THORONDOR DAILY BRIEFING — {datetime.now().strftime("%Y-%m-%d")}', '']
    
    if tier1:
        lines.append('🔴 TIER 1 — MUST KNOW')
        for a in tier1:
            lines.append(f'• [{a["title"]}]({a["url"]})')
        lines.append('')
    
    if tier2:
        lines.append('🟡 TIER 2 — RANKED FOR YOU')
        for a in tier2:
            lines.append(f'• [{a["title"]}]({a["url"]})')
        lines.append('')
    
    if not tier1 and not tier2:
        lines.append('No new articles today.')
    
    return '\n'.join(lines), [a['id'] for a in tier1 + tier2]

async def send_digest(context: ContextTypes.DEFAULT_TYPE):
    text, article_ids = format_digest()
    if not article_ids:
        return
    
    keyboard = [[
        InlineKeyboardButton('👍', callback_data=f'like:{article_ids[0]}'),
        InlineKeyboardButton('👎', callback_data=f'dislike:{article_ids[0]}'),
        InlineKeyboardButton('✓ Read', callback_data=f'open:{article_ids[0]}'),
        InlineKeyboardButton('★ Save', callback_data=f'save:{article_ids[0]}')
    ]]
    
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text=text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True
    )
    mark_notified(article_ids)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🦅 Thorondor is online. Use /digest for latest brief.')

async def digest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_digest(context)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action, article_id = query.data.split(':')
    article_id = int(article_id)
    
    log_interaction(article_id, action)
    
    feedback = {'like': '👍 Liked', 'dislike': '👎 Disliked', 'open': '✓ Marked read', 'save': '★ Saved'}.get(action, action)
    await query.edit_message_reply_markup(reply_markup=None)
    await context.bot.send_message(chat_id=CHAT_ID, text=f'{feedback} article #{article_id}')

def main():
    if not TELEGRAM_TOKEN:
        logger.error('TELEGRAM_BOT_TOKEN not set')
        return
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('digest', digest_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info('Thorondor bot starting...')
    app.run_polling()

if __name__ == '__main__':
    main()