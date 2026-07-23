#!/usr/bin/env python3
import os
import subprocess
from dotenv import load_dotenv
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database import (
    get_unnotified_articles,
    get_unnotified_articles_by_source,
    get_most_recent_article_by_source,
    mark_notified,
    get_sources,
    add_x_user, delete_x_user, get_x_users
)

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def format_digest():
    # Lazy import to avoid loading sentence-transformers on bot startup
    from intelligence import generate_summary

    lines = []
    article_ids = []

    # ── Tier 1: Anduril changes ─────────────────────────────────
    anduril = get_unnotified_articles_by_source('Anduril', limit=5)
    if anduril:
        lines.append('🔴 TIER 1 — ANDURIL CHANGES')
        for a in anduril:
            summary = generate_summary(a['title'], a['summary'] or '', 'defense tech, AI, startups')
            if len(summary) > 150:
                summary = summary[:150].rsplit(' ', 1)[0] + '...'
            lines.append(f"• [{a['title']}]({a['url']})")
            lines.append(f"  _{summary}_")
            article_ids.append(a['id'])
        lines.append('')

    # ── Tier 1: X Tweets ────────────────────────────────────────
    x_all = get_unnotified_articles(tier=1, limit=50)
    x_by_user = {}
    for a in x_all:
        if a['source_type'] != 'x_api':
            continue
        if a['source'] not in x_by_user:
            x_by_user[a['source']] = []
        x_by_user[a['source']].append(a)

    x_lines = []
    x_ids = []
    for username, tweets in x_by_user.items():
        for tweet in tweets[:3]:
            summary = generate_summary(tweet['title'], tweet['summary'] or '', 'defense tech, AI, startups')
            if len(summary) > 150:
                summary = summary[:150].rsplit(' ', 1)[0] + '...'
            x_lines.append(f"• [{tweet['title']}]({tweet['url']})")
            x_lines.append(f"  _{summary}_")
            x_ids.append(tweet['id'])

    if x_lines:
        lines.append('🔴 TIER 1 — X POSTS')
        lines.extend(x_lines)
        lines.append('')
        article_ids.extend(x_ids)
    else:
        lines.append('🔴 TIER 1 — X POSTS')
        lines.append('_No new X posts._')
        lines.append('')

    # ── Tier 2: RSS ── 1 most recent per feed (persists until newer) ─
    rss_sources = get_sources(source_type='rss', active_only=True)
    rss_lines = []
    rss_ids = []
    for source in rss_sources:
        article = get_most_recent_article_by_source(source['name'])
        if article:
            summary = generate_summary(article['title'], article['summary'] or '', 'defense tech, AI, startups')
            if len(summary) > 150:
                summary = summary[:150].rsplit(' ', 1)[0] + '...'
            rss_lines.append(f"• [{article['title']}]({article['url']})")
            rss_lines.append(f"  _{summary}_")
            rss_ids.append(article['id'])

    if rss_lines:
        lines.append('🟡 TIER 2 — RSS')
        lines.extend(rss_lines)
        lines.append('')
        article_ids.extend(rss_ids)

    if not article_ids:
        return 'No new articles today.', []

    date_str = datetime.now().strftime('%Y-%m-%d')
    header = f'🦅 THORONDOR DAILY BRIEFING — {date_str}\n\n'
    return header + '\n'.join(lines), article_ids


async def send_digest(context: ContextTypes.DEFAULT_TYPE):
    text, article_ids = format_digest()
    if not article_ids:
        return

    await context.bot.send_message(
        chat_id=CHAT_ID,
        text=text,
        parse_mode='Markdown',
        disable_web_page_preview=True
    )
    mark_notified(article_ids)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🦅 Thorondor is online. Use /commands for available commands.')


async def commands_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '🦅 Thorondor Commands:\n\n'
        '/digest — latest brief\n'
        '/add <username> — watch an X account (Tier 1)\n'
        '/delete <username> — stop watching\n'
        '/list — show monitored accounts\n'
        '/update — pull latest code from GitHub\n'
        '/commands — show this list'
    )


async def digest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_digest(context)


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text('Usage: /add <username>')
        return
    username = context.args[0].lstrip('@')
    if add_x_user(username, tier=1):
        await update.message.reply_text(f'✅ @{username} added to Tier 1 watch list.')
    else:
        await update.message.reply_text(f'⚠️ Failed to add @{username} (already exists?).')


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text('Usage: /delete <username>')
        return
    username = context.args[0].lstrip('@')
    delete_x_user(username)
    await update.message.reply_text(f'🗑️ @{username} removed from watch list.')


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = get_x_users(active_only=True)
    if not users:
        await update.message.reply_text('No X users being monitored. Use /add <username> to add.')
        return
    lines = ['📋 Monitored X accounts (Tier 1):']
    for u in users:
        lines.append(f'• @{u["username"]}')
    await update.message.reply_text('\n'.join(lines))


async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🔄 Pulling latest code...')
    try:
        result = subprocess.run(
            ['git', 'pull'],
            cwd='/opt/thorondor',
            capture_output=True,
            text=True,
            timeout=30
        )
        output = result.stdout.strip() or result.stderr.strip() or 'No output'
        await update.message.reply_text(f'Git pull result:\n```\n{output[:500]}\n```')
    except Exception as e:
        await update.message.reply_text(f'❌ Git pull failed: {e}')


def main():
    if not TELEGRAM_TOKEN:
        logger.error('TELEGRAM_BOT_TOKEN not set')
        return

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('commands', commands_command))
    app.add_handler(CommandHandler('digest', digest_command))
    app.add_handler(CommandHandler('add', add_command))
    app.add_handler(CommandHandler('delete', delete_command))
    app.add_handler(CommandHandler('list', list_command))
    app.add_handler(CommandHandler('update', update_command))

    logger.info('Thorondor bot starting...')
    app.run_polling()


if __name__ == '__main__':
    main()