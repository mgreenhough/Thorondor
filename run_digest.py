#!/usr/bin/env python3
"""
Thorondor Daily Digest — One-shot script.
Runs scrapers, builds digest, sends to Telegram, marks articles notified, exits.
"""
import os
import sys
import logging
import sqlite3
from datetime import datetime

from dotenv import load_dotenv
import requests

load_dotenv()

from database import (
    DB_PATH,
    get_unnotified_articles,
    get_unnotified_articles_by_source,
    mark_notified,
    get_sources,
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


def clear_backlog():
    """Mark all old unnotified articles as notified so they don't accumulate."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("UPDATE articles SET is_notified = 1 WHERE is_notified = 0")
    count = cur.rowcount
    conn.commit()
    conn.close()
    if count:
        logger.info(f'Cleared backlog: marked {count} old articles as notified')
    return count


def send_telegram_message(text: str) -> bool:
    """Send a plain text message via Telegram Bot API (one-shot, no polling)."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error('TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set')
        return False

    # Hard cap at 3500 chars to stay well under Telegram's 4096 limit
    if len(text) > 3500:
        text = text[:3490].rsplit('\n', 1)[0]
        text += '\n\n_(truncated)_'

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
    lines = []
    article_ids = []

    # ── Tier 1: Anduril ─────────────────────────────────────────
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
        for tweet in tweets[:3]:  # max 3 per user
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

    # ── Tier 2: RSS ── 1 most recent per feed ───────────────────
    rss_sources = get_sources(source_type='rss', active_only=True)
    rss_lines = []
    rss_ids = []
    for source in rss_sources:
        articles = get_unnotified_articles_by_source(source['name'], limit=1)
        if articles:
            a = articles[0]
            summary = generate_summary(a['title'], a['summary'] or '', 'defense tech, AI, startups')
            if len(summary) > 150:
                summary = summary[:150].rsplit(' ', 1)[0] + '...'
            rss_lines.append(f"• [{a['title']}]({a['url']})")
            rss_lines.append(f"  _{summary}_")
            rss_ids.append(a['id'])

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


def main() -> int:
    logger.info('=== THORONDOR DAILY DIGEST ===')

    # 0. Clear any backlog from previous failed runs
    clear_backlog()

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