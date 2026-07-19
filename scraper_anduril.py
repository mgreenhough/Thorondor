#!/usr/bin/env python3
import requests
import hashlib
from bs4 import BeautifulSoup
from database import add_article
from urllib.parse import urljoin, urlparse

BASE_URL = 'https://www.anduril.com'
BLOG_URL = 'https://www.anduril.com/article'
RSS_URL = 'https://www.anduril.com/rss'

def fetch_page(url):
    try:
        r = requests.get(url, timeout=30, headers={'User-Agent': 'ThorondorBot/1.0'})
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f'Error fetching {url}: {e}')
        return None

def try_rss_feed():
    try:
        r = requests.get(RSS_URL, timeout=30, headers={'User-Agent': 'ThorondorBot/1.0'})
        if r.status_code == 200:
            import feedparser
            feed = feedparser.parse(r.content)
            articles = []
            for entry in feed.entries:
                articles.append({
                    'title': entry.get('title', 'No title'),
                    'url': entry.get('link', ''),
                    'summary': entry.get('summary', '')[:500],
                    'content_hash': hashlib.sha256(entry.get('link', '').encode()).hexdigest()[:16]
                })
            return articles
    except Exception as e:
        print(f'RSS feed failed: {e}')
    return []

def scrape_blog_page(url):
    html = fetch_page(url)
    if not html:
        return []
    
    soup = BeautifulSoup(html, 'lxml')
    articles = []
    
    # Look for article cards/links
    for article in soup.find_all(['article', 'a', 'div']):
        link = article.get('href') if article.name == 'a' else article.find('a', href=True)
        if not link:
            continue
        
        href = link['href'] if isinstance(link, dict) else link.get('href', '')
        if not href:
            continue
            
        full_url = urljoin(url, href)
        
        # Filter for article pages
        if '/article' in full_url or '/blog' in full_url or '/news' in full_url:
            title = article.get_text(strip=True)[:200]
            if len(title) > 10:
                content_hash = hashlib.sha256(full_url.encode()).hexdigest()[:16]
                articles.append({
                    'title': title,
                    'url': full_url,
                    'summary': '',
                    'content_hash': content_hash
                })
    
    # Remove duplicates by URL
    seen = set()
    unique = []
    for a in articles:
        if a['url'] not in seen:
            seen.add(a['url'])
            unique.append(a)
    
    return unique

def run_anduril_scraper():
    # Try RSS first
    articles = try_rss_feed()
    source_method = 'RSS'
    
    # Fallback to blog scraping
    if not articles:
        articles = scrape_blog_page(BLOG_URL)
        source_method = 'blog scrape'
    
    total_new = 0
    for article in articles:
        added = add_article(
            title=article['title'],
            summary=article['summary'],
            url=article['url'],
            source='Anduril',
            source_type='anduril',
            tier=1,
            content_hash=article['content_hash']
        )
        if added:
            total_new += 1
    
    print(f'Anduril scraper complete ({source_method}). New articles: {total_new}')
    return total_new

if __name__ == '__main__':
    run_anduril_scraper()