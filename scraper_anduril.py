#!/usr/bin/env python3
import requests
import hashlib
from bs4 import BeautifulSoup
from database import add_article
from urllib.parse import urljoin

BASE_URL = 'https://www.anduril.com'

def fetch_page(url):
    try:
        r = requests.get(url, timeout=30, headers={'User-Agent': 'ThorondorBot/1.0'})
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f'Error fetching {url}: {e}')
        return None

def extract_articles(html, base_url):
    soup = BeautifulSoup(html, 'lxml')
    articles = []
    
    for link in soup.find_all('a', href=True):
        href = link['href']
        full_url = urljoin(base_url, href)
        
        if any(p in full_url for p in ['/article', '/blog', '/news', '/press']):
            title = link.get_text(strip=True)
            if title and len(title) > 10:
                content_hash = hashlib.sha256(full_url.encode()).hexdigest()[:16]
                articles.append({
                    'title': title,
                    'url': full_url,
                    'summary': '',
                    'content_hash': content_hash
                })
    
    return articles

def run_anduril_scraper():
    html = fetch_page(BASE_URL)
    if not html:
        return 0
    
    articles = extract_articles(html, BASE_URL)
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
    
    print(f'Anduril scraper complete. New articles: {total_new}')
    return total_new

if __name__ == '__main__':
    run_anduril_scraper()