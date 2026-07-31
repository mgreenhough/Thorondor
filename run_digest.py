#!/usr/bin/env python3
"""
Thorondor Daily Digest — One-shot script.
Runs scrapers, builds digest, sends to Telegram, marks articles notified, exits.
"""
import os
import sys
import logging
import traceback
from datetime import datetime

from dotenv import load_dotenv
import requests

load_dotenv()

from database import (
    get_unnotified_articles,
    get_unnotified_articles_by_source,
    get_most_recent_article_by_source,
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


def _strip_markdown(text: str) -> str:
    """Strip characters that Telegram Markdown parser treats as special."""
    return text.replace('_', '\\_').replace('*', '\\*').replace('`', '\\`')


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

    # Try Markdown first
    payload_md = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True
    }

    try:
        resp = requests.post(url, json=payload_md, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        if result.get('ok'):
            logger.info('Digest sent successfully')
            return True
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 400:
            logger.warning('Telegram rejected Markdown; retrying as plain text')
        else:
            logger.error(f'Telegram API HTTP error: {e}')
            return False
    except Exception as e:
        logger.error(f'Failed to send Telegram Markdown message: {e}')
        return False

    # Fallback: send as plain text (strip Markdown syntax)
    payload_plain = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': _strip_markdown(text),
        'disable_web_page_preview': True
    }

    try:
        resp = requests.post(url, json=payload_plain, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        if result.get('ok'):
            logger.info('Digest sent successfully (plain text fallback)')
            return True
        else:
            logger.error(f'Telegram API error (plain): {result}')
            return False
    except Exception as e:
        logger.error(f'Failed to send Telegram plain message: {e}')
        return False


def _safe_run(name, fn):
    """Run a scraper/monitor, catching and logging any exception."""
    try:
        return fn()
    except Exception:
        logger.error(f'{name} crashed:\n{traceback.format_exc()}')
        return 0


def format_digest() -> tuple[str, list[int]]:
    """Build the markdown digest and return (text, article_ids)."""
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
    else:
        lines.append('🔴 TIER 1 — X POSTS')
        lines.append('_No new X posts._')
        lines.append('')

    # ── Tier 2: RSS ── 1 most recent per feed (persists until newer) ─
    rss_sources = get_sources(source_type='rss', active_only=True)
    rss_lines = []
    rss_ids = []
    for source in rss_sources:
        # Get most recent article for this source, regardless of is_notified
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


def main() -> int:
    logger.info('=== THORONDOR DAILY DIGEST ===')

    # 1. Collect articles — each step is wrapped so a crash in one
    #    doesn't kill the whole digest
    logger.info('Running Anduril scraper...')
    anduril_count = _safe_run('Anduril scraper', run_anduril_scraper)

    logger.info('Running X monitor...')
    x_count = _safe_run('X monitor', run_x_monitor)

    logger.info('Running RSS aggregator...')
    rss_count = _safe_run('RSS aggregator', run_rss_aggregator)

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