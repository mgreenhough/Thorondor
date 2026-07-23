#!/usr/bin/env python3
"""
Anduril Full-Site Change Detector

Crawls every page on anduril.com, hashes the cleaned text content,
and reports ANY changes as Tier 1 articles.  Heavy rate limiting —
we have 23+ hours between runs so we never hammer their server.
"""
import os
import sys
import re
import hashlib
import time
import logging
from urllib.parse import urljoin, urlparse
from collections import deque

import requests
from bs4 import BeautifulSoup

from database import add_article, get_page_snapshot, upsert_page_snapshot

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ─── Configuration ───────────────────────────────────────────────
BASE_URL = 'https://www.anduril.com'
DOMAIN = 'anduril.com'
REQUEST_DELAY_SECONDS = 2.0   # polite crawl — 2s between requests
MAX_PAGES = 500               # safety cap
TIMEOUT = 30

# File extensions to skip
SKIP_EXTENSIONS = {
    '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp',
    '.mp4', '.mov', '.avi', '.mp3', '.wav',
    '.zip', '.tar', '.gz', '.rar', '.exe', '.dmg',
    '.css', '.js', '.woff', '.woff2', '.ttf', '.eot',
}

# Text snippets to strip from cleaned content (boilerplate)
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
    """Return True if URL should be ignored."""
    parsed = urlparse(url)
    # Must be anduril.com domain
    if DOMAIN not in parsed.netloc.lower():
        return True
    # Skip fragments (same page anchors)
    if parsed.fragment and not parsed.path and not parsed.query:
        return True
    # Skip known file extensions
    path_lower = parsed.path.lower()
    if any(path_lower.endswith(ext) for ext in SKIP_EXTENSIONS):
        return True
    # Skip common non-content paths
    skip_paths = {'/cdn-cgi/', '/wp-json/', '/xmlrpc.php'}
    if any(path_lower.startswith(sp) for sp in skip_paths):
        return True
    return False


def normalize_url(url, base):
    """Resolve relative URL, strip fragment, force https."""
    full = urljoin(base, url)
    parsed = urlparse(full)
    # Strip fragment, force lowercase netloc
    clean = f"https://{parsed.netloc.lower()}{parsed.path}"
    if parsed.query:
        clean += f"?{parsed.query}"
    return clean


def fetch_page(url):
    """Fetch a page with polite delay. Returns (status, html_text)."""
    try:
        resp = requests.get(
            url,
            timeout=TIMEOUT,
            headers={'User-Agent': 'ThorondorBot/1.0 (+https://github.com/mgreenhough/Thorondor)'}
        )
        resp.raise_for_status()
        time.sleep(REQUEST_DELAY_SECONDS)
        return resp.status_code, resp.text
    except Exception as e:
        logger.warning(f'Failed to fetch {url}: {e}')
        return None, None


def extract_clean_text(html, url):
    """
    Strip nav, scripts, styles, footers.
    Return cleaned text suitable for hashing and preview.
    """
    soup = BeautifulSoup(html, 'lxml')

    # Remove tags that are never content
    for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'iframe', 'noscript']):
        tag.decompose()

    # Remove elements with common nav/footer class/id names
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

    # Try to find the main content area first
    main = soup.find('main') or soup.find('article') or soup.find(role='main')
    if main:
        text = main.get_text(separator='\n')
    else:
        text = soup.get_text(separator='\n')

    # Clean up whitespace
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Skip boilerplate lines
        if any(pat.match(line) for pat in BOILERPLATE_PATTERNS):
            continue
        lines.append(line)

    cleaned = '\n'.join(lines)
    return cleaned


def get_text_preview(text, max_chars=300):
    """Return a short preview of the text."""
    preview = text.replace('\n', ' ').strip()
    if len(preview) > max_chars:
        preview = preview[:max_chars].rsplit(' ', 1)[0] + '...'
    return preview


def discover_links(html, base_url):
    """Find all internal links on a page."""
    soup = BeautifulSoup(html, 'lxml')
    found = set()
    for tag in soup.find_all('a', href=True):
        href = tag['href']
        # Skip mailto, tel, javascript
        if href.startswith(('mailto:', 'tel:', 'javascript:')):
            continue
        full = normalize_url(href, base_url)
        if not should_skip_url(full):
            found.add(full)
    return found


def run_anduril_scraper():
    logger.info('=== Anduril Full-Site Change Detector ===')
    logger.info(f'Starting crawl at {BASE_URL} with {REQUEST_DELAY_SECONDS}s delay')

    queue = deque([BASE_URL])
    seen = {BASE_URL}
    checked = 0
    changed = 0
    new_pages = 0

    while queue and checked < MAX_PAGES:
        url = queue.popleft()
        checked += 1

        # Fetch
        status, html = fetch_page(url)
        if html is None:
            logger.warning(f'  [{checked}] SKIP (fetch failed): {url}')
            continue

        # Extract and hash
        cleaned_text = extract_clean_text(html, url)
        text_hash = hashlib.sha256(cleaned_text.encode('utf-8')).hexdigest()
        preview = get_text_preview(cleaned_text)

        # Compare to snapshot
        snapshot = get_page_snapshot(url)
        if snapshot is None:
            # Brand new page
            logger.info(f'  [{checked}] NEW PAGE: {url}')
            upsert_page_snapshot(url, DOMAIN, text_hash, preview)
            add_article(
                title=f'Anduril — New page: {urlparse(url).path or "/"}',
                summary=preview,
                url=url,
                source='Anduril',
                source_type='anduril',
                tier=1,
                content_hash=text_hash
            )
            new_pages += 1
        elif snapshot['content_hash'] != text_hash:
            # Page changed
            logger.info(f'  [{checked}] CHANGED: {url}')
            upsert_page_snapshot(url, DOMAIN, text_hash, preview)
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
            # Unchanged — just update last_seen
            upsert_page_snapshot(url, DOMAIN, text_hash, preview)
            logger.debug(f'  [{checked}] unchanged: {url}')

        # Discover more links
        for link in discover_links(html, url):
            if link not in seen:
                seen.add(link)
                queue.append(link)

    logger.info(f'Crawl complete. Checked {checked} pages. New: {new_pages}, Changed: {changed}')
    return new_pages + changed


if __name__ == '__main__':
    sys.exit(run_anduril_scraper())