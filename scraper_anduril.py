#!/usr/bin/env python3
"""
Anduril Full-Site Change Detector

Crawls every page on anduril.com, hashes the cleaned text content,
and reports ANY changes as Tier 1 articles.  Heavy rate limiting.

Uses 2-consecutive-change rule: a hash must match for 2 crawls
before it's reported as a change. This eliminates one-off dynamic
noise (timestamps, scripts, A/B tests).
"""
import os
import sys
import re
import hashlib
import time
import logging
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin, urlparse
from collections import deque
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

from database import add_article, get_page_snapshot, upsert_page_snapshot, confirm_pending_hash

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ─── Configuration ───────────────────────────────────────────────
BASE_URL = 'https://www.anduril.com'
DOMAIN = 'anduril.com'
REQUEST_DELAY_SECONDS = 2.0
MAX_PAGES = 500
TIMEOUT = 30
AGE_CUTOFF_HOURS = 36  # skip changes to pages older than this

# File extensions to skip
SKIP_EXTENSIONS = {
    '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp',
    '.mp4', '.mov', '.avi', '.mp3', '.wav',
    '.zip', '.tar', '.gz', '.rar', '.exe', '.dmg',
    '.css', '.js', '.woff', '.woff2', '.ttf', '.eot',
}

BOILERPLATE_PATTERNS = [
    re.compile(r'^\s*careers\s*$', re.I),
    re.compile(r'^\s*contact\s*$', re.I),
    re.compile(r'^\s*privacy policy\s*$', re.I),
    re.compile(r'^\s*terms of (use|service)\s*$', re.I),
    re.compile(r'^\s*cookie policy\s*$', re.I),
    re.compile(r'^\s*accessibility\s*$', re.I),
    re.compile(r'^\s*subscribe\s*$', re.I),
    re.compile(r'^\s*follow us\s*$', re.I),
    re.compile(r'^\s*all rights reserved\.?\s*$', re.I),
]


def should_skip_url(url):
    parsed = urlparse(url)
    if DOMAIN not in parsed.netloc.lower():
        return True
    if parsed.fragment and not parsed.path and not parsed.query:
        return True
    path_lower = parsed.path.lower()
    if any(path_lower.endswith(ext) for ext in SKIP_EXTENSIONS):
        return True
    skip_paths = {'/cdn-cgi/', '/wp-json/', '/xmlrpc.php'}
    if any(path_lower.startswith(sp) for sp in skip_paths):
        return True
    return False


def normalize_url(url, base):
    full = urljoin(base, url)
    parsed = urlparse(full)
    clean = f"https://{parsed.netloc.lower()}{parsed.path}"
    if parsed.query:
        clean += f"?{parsed.query}"
    return clean


def fetch_page(url):
    try:
        resp = requests.get(
            url,
            timeout=TIMEOUT,
            headers={'User-Agent': 'ThorondorBot/1.0'}
        )
        resp.raise_for_status()
        time.sleep(REQUEST_DELAY_SECONDS)
        return resp.status_code, resp.text
    except Exception as e:
        logger.warning(f'Failed to fetch {url}: {e}')
        return None, None


def extract_clean_text(html, url):
    soup = BeautifulSoup(html, 'lxml')
    for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'iframe', 'noscript']):
        tag.decompose()

    noise_selectors = [
        'header', '.header', '#header',
        '.navigation', '#navigation', '.nav', '#nav',
        '.menu', '#menu', '.sidebar', '#sidebar',
        '.footer', '#footer', '.bottom', '#bottom',
        '.cookie-banner', '#cookie-banner', '.gdpr', '#gdpr',
        '.newsletter', '#newsletter', '.subscribe', '#subscribe',
    ]
    for selector in noise_selectors:
        for el in soup.select(selector):
            el.decompose()

    main = soup.find('main') or soup.find('article') or soup.find(role='main')
    if main:
        text = main.get_text(separator='\n')
    else:
        text = soup.get_text(separator='\n')

    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if any(pat.match(line) for pat in BOILERPLATE_PATTERNS):
            continue
        lines.append(line)

    return '\n'.join(lines)


def get_text_preview(text, max_chars=300):
    preview = text.replace('\n', ' ').strip()
    if len(preview) > max_chars:
        preview = preview[:max_chars].rsplit(' ', 1)[0] + '...'
    return preview


def discover_links(html, base_url):
    soup = BeautifulSoup(html, 'lxml')
    found = set()
    for tag in soup.find_all('a', href=True):
        href = tag['href']
        if href.startswith(('mailto:', 'tel:', 'javascript:')):
            continue
        full = normalize_url(href, base_url)
        if not should_skip_url(full):
            found.add(full)
    return found


def parse_sitemap_date(date_str):
    """Parse ISO 8601 date string from sitemap to datetime (UTC)."""
    if not date_str:
        return None
    date_str = date_str.strip()
    formats = [
        '%Y-%m-%dT%H:%M:%S.%fZ',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%dT%H:%M:%S.%f%z',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%d',
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def discover_via_sitemap():
    """Try to find all URLs via sitemap.xml, returning {url: lastmod_datetime}."""
    url_dates = {}
    sitemap_urls = [
        'https://www.anduril.com/sitemap.xml',
        'https://www.anduril.com/sitemap_index.xml',
    ]
    for sitemap_url in sitemap_urls:
        status, html = fetch_page(sitemap_url)
        if html is None:
            continue
        try:
            root = ET.fromstring(html.encode('utf-8'))
            ns_sitemap = 'http://www.sitemaps.org/schemas/sitemap/0.9'
            ns_news = 'http://www.google.com/schemas/sitemap-news/0.9'

            for url_elem in root.iter(f'{{{ns_sitemap}}}url'):
                loc = url_elem.find(f'{{{ns_sitemap}}}loc')
                if loc is None or not loc.text:
                    continue
                page_url = loc.text.strip()

                news_elem = url_elem.find(f'{{{ns_news}}}news')
                if news_elem is not None:
                    pub_date = news_elem.find(f'{{{ns_news}}}publication_date')
                    if pub_date is not None and pub_date.text:
                        dt = parse_sitemap_date(pub_date.text.strip())
                        if dt:
                            url_dates[page_url] = dt
                            continue

                lastmod = url_elem.find(f'{{{ns_sitemap}}}lastmod')
                if lastmod is not None and lastmod.text:
                    dt = parse_sitemap_date(lastmod.text.strip())
                    if dt:
                        url_dates[page_url] = dt

        except Exception as e:
            logger.warning(f'Sitemap parse failed for {sitemap_url}: {e}')
    return url_dates


def is_page_recent(lastmod_dt, cutoff_hours=AGE_CUTOFF_HOURS):
    """Return True if lastmod is within cutoff_hours of now."""
    if lastmod_dt is None:
        return False  # No sitemap date = can't verify recency, skip
    now = datetime.now(timezone.utc)
    age = now - lastmod_dt
    return age <= timedelta(hours=cutoff_hours)


def run_anduril_scraper():
    logger.info('=== Anduril Full-Site Change Detector ===')

    queue = deque([BASE_URL])
    seen = {BASE_URL}

    sitemap_dates = discover_via_sitemap()
    logger.info(f'Sitemap discovered {len(sitemap_dates)} URLs')
    for url in sitemap_dates:
        if url not in seen:
            seen.add(url)
            queue.append(url)

    checked = 0
    changed = 0
    new_pages = 0
    pending = 0
    skipped_old = 0
    MAX_CHANGES = 5

    while queue and checked < MAX_PAGES:
        url = queue.popleft()
        checked += 1

        status, html = fetch_page(url)
        if html is None:
            logger.warning(f'  [{checked}] SKIP (fetch failed): {url}')
            continue

        cleaned_text = extract_clean_text(html, url)
        text_hash = hashlib.sha256(cleaned_text.encode('utf-8')).hexdigest()
        preview = get_text_preview(cleaned_text)

        sitemap_date = sitemap_dates.get(url)

        snapshot = get_page_snapshot(url)
        if snapshot is None:
            # First time — baseline only
            logger.info(f'  [{checked}] Baseline: {url}')
            upsert_page_snapshot(url, DOMAIN, text_hash, preview)
            new_pages += 1
            continue

        stored_hash = snapshot['content_hash']
        pending_hash = snapshot.get('pending_hash')

        if text_hash == stored_hash:
            # Unchanged — clear any stale pending hash
            if pending_hash is not None:
                confirm_pending_hash(url, stored_hash, snapshot.get('text_preview', ''))
            upsert_page_snapshot(url, DOMAIN, text_hash, preview)
        elif text_hash == pending_hash:
            # Same as last crawl's pending hash → CONFIRMED CHANGE
            if is_page_recent(sitemap_date):
                if changed < MAX_CHANGES:
                    logger.info(f'  [{checked}] CHANGED (confirmed): {url}')
                    confirm_pending_hash(url, text_hash, preview)
                    add_article(
                        title=f'Anduril — Page changed: {urlparse(url).path or "/"}',
                        summary=preview,
                        url=url,
                        source='Anduril',
                        source_type='anduril',
                        tier=1,
                        content_hash=text_hash
                    )
                    changed += 1
                else:
                    logger.info(f'  [{checked}] CHANGED (cap reached): {url}')
                    confirm_pending_hash(url, text_hash, preview)
            else:
                age_str = str(datetime.now(timezone.utc) - sitemap_date) if sitemap_date else 'unknown'
                logger.info(f'  [{checked}] CHANGED (old, skipped): {url} (age: {age_str})')
                confirm_pending_hash(url, text_hash, preview)
                skipped_old += 1
        else:
            # New hash, but different from both stored and pending
            # → store as pending, wait for next crawl to confirm
            logger.info(f'  [{checked}] PENDING (unconfirmed): {url}')
            upsert_page_snapshot(url, DOMAIN, stored_hash, preview, pending_hash=text_hash)
            pending += 1

        for link in discover_links(html, url):
            if link not in seen:
                seen.add(link)
                queue.append(link)

    logger.info(f'Crawl complete. Checked {checked}, Baseline: {new_pages}, Pending: {pending}, Confirmed: {changed}, Skipped(old): {skipped_old}')
    return changed


if __name__ == '__main__':
    sys.exit(run_anduril_scraper())