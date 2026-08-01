#!/usr/bin/env python3
import os
import subprocess
import asyncio
from dotenv import load_dotenv
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database import (
    add_x_user, delete_x_user, get_x_users
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(SCRIPT_DIR, '.env')
if os.path.isfile(dotenv_path):
    load_dotenv(dotenv_path)
else:
    load_dotenv()  # fallback

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🦅 Thorondor is online. Use /commands for available commands.')


async def commands_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '🦅 Thorondor Commands:\n\n'
        '/digest — run daily digest now\n'
        '/add <username> — watch an X account (Tier 1)\n'
        '/delete <username> — stop watching\n'
        '/list — show monitored accounts\n'
        '/update — pull latest code from GitHub\n'
        '/commands — show this list'
    )


async def digest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Run the digest as a one-shot subprocess (does not load ML models in bot)."""
    await update.message.reply_text('🔄 Running digest...')

    # Determine project root (same dir as this script)
    project_dir = os.path.dirname(os.path.abspath(__file__))

    # Use venv Python explicitly so packages and .env are always available
    venv_python = os.path.join(project_dir, 'venv', 'bin', 'python3')
    if not os.path.isfile(venv_python):
        venv_python = 'python3'  # fallback

    # Run run_digest.py in background so bot stays responsive
    proc = await asyncio.create_subprocess_exec(
        venv_python, 'run_digest.py',
        cwd=project_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await proc.communicate()

    if proc.returncode == 0:
        await update.message.reply_text('✅ Digest completed.')
    else:
        err = stderr.decode()[:400] or stdout.decode()[:400] or 'Unknown error'
        await update.message.reply_text(f'❌ Digest failed:\n```\n{err}\n```')


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
            cwd=os.path.dirname(os.path.abspath(__file__)),
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