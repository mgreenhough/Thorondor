#!/usr/bin/env python3
"""
Thorondor Daily Digest — One-shot script.
Runs scrapers, builds digest, sends to Telegram, marks articles notified, exits.
"""
import os
import sys
import logging
from datetime import datetime

from dotenv import load_dotenv
import requests

load_dotenv()

from database import (
    get_unnotified_articles,
    mark_notified,
    add_article,
    get_sources,
    update_source_last_fetched
)
from scraper_anduril import run_anduril_scraper
from monitor_x import run_x_monitor
from feed_rss import run_rss_aggregator
from intelligence import generate_summary

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


def send_telegram_message(text: str) -> bool:
    """Send a plain text message via Telegram Bot API (one-shot, no polling)."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error('TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set')
        return False

    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True
    }

    try:
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        if result.get('ok'):
            logger.info('Digest sent successfully')
            return True
        else:
            logger.error(f'Telegram API error: {result}')
            return False
    except Exception as e:
        logger.error(f'Failed to send Telegram message: {e}')
        return False


def format_digest() -> tuple[str, list[int]]:
    """Build the markdown digest and return (text, article_ids)."""
    tier1 = get_unnotified_articles(tier=1, limit=5)
    tier2 = get_unnotified_articles(tier=2, limit=10)

    date_str = datetime.now().strftime('%Y-%m-%d')
    lines = [f'🦅 THORONDOR DAILY BRIEFING — {date_str}', '']

    if tier1:
        lines.append('🔴 TIER 1 — MUST KNOW')
        for a in tier1:
            summary = generate_summary(a['title'], a['summary'] or '', 'defense tech, AI, startups')
            lines.append(f"• [{a['title']}]({a['url']})")
            lines.append(f"  _{summary}_")
        lines.append('')

    if tier2:
        lines.append('🟡 TIER 2 — RANKED FOR YOU')
        for a in tier2:
            summary = generate_summary(a['title'], a['summary'] or '', 'defense tech, AI, startups')
            lines.append(f"• [{a['title']}]({a['url']})")
            lines.append(f"  _{summary}_")
        lines.append('')

    if not tier1 and not tier2:
        lines.append('No new articles today.')

    article_ids = [a['id'] for a in tier1 + tier2]
    return '\n'.join(lines), article_ids


def main() -> int:
    logger.info('=== THORONDOR DAILY DIGEST ===')

    # 1. Collect articles
    logger.info('Running Anduril scraper...')
    anduril_count = run_anduril_scraper()

    logger.info('Running X monitor...')
    x_count = run_x_monitor()

    logger.info('Running RSS aggregator...')
    rss_count = run_rss_aggregator()

    logger.info(f'Collection complete: {anduril_count} Anduril, {x_count} X, {rss_count} RSS')

    # 2. Build digest
    text, article_ids = format_digest()

    if not article_ids:
        logger.info('No new articles to send.')
        return 0

    logger.info(f'Digest contains {len(article_ids)} articles')

    # 3. Send digest
    if send_telegram_message(text):
        # 4. Mark as notified only on success
        mark_notified(article_ids)
        logger.info('Digest completed and articles marked notified')
        return 0
    else:
        logger.error('Digest failed to send — articles remain unnotified for retry')
        return 1


if __name__ == '__main__':
    sys.exit(main())