#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup

urls = [
    'https://www.anduril.com/news',
    'https://www.anduril.com/press',
    'https://www.anduril.com/blog',
    'https://www.anduril.com/about',
    'https://www.anduril.com/careers',
    'https://www.anduril.com/',
]

for url in urls:
    try:
        resp = requests.get(url, headers={'User-Agent': 'ThorondorBot/1.0'}, timeout=10, allow_redirects=True)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        pub = soup.find('meta', property='article:published_time') or soup.find('meta', attrs={'name': 'article:published_time'})
        mod = soup.find('meta', property='article:modified_time') or soup.find('meta', attrs={'name': 'article:modified_time'})
        
        times = soup.find_all('time')[:2]
        time_strs = [t.get('datetime') for t in times if t.get('datetime')]
        
        print(f"URL: {resp.url}")
        print(f"  published_time: {pub.get('content') if pub else None}")
        print(f"  modified_time: {mod.get('content') if mod else None}")
        print(f"  time tags: {time_strs}")
        print()
    except Exception as e:
        print(f"URL: {url} ERROR: {e}")
        print()