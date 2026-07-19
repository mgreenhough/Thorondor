#!/usr/bin/env python3
import feedparser
import requests
from database import add_article, get_sources, update_source_last_fetched
from datetime import datetime

def fetch_rss_feed(url, source_name):
    try:
        response = requests.get(url, timeout=30, headers={'User-Agent': 'ThorondorBot/1.0'})
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        
        articles = []
        for entry in feed.entries:
            title = entry.get('title', 'No title')
            link = entry.get('link', '')
            summary = entry.get('summary', entry.get('description', ''))
            published = entry.get('published', '')
            
            published_dt = None
            if published:
                try:
                    published_dt = datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') else None
                except:
                    pass
            
            articles.append({
                'title': title,
                'url': link,
                'summary': summary[:500] if summary else '',
                'published_at': published_dt
            })
        
        return articles
    except Exception as e:
        print(f'Error fetching {source_name}: {e}')
        return []

def run_rss_aggregator():
    sources = get_sources(source_type='rss', active_only=True)
    total_new = 0
    
    for source in sources:
        print(f'Fetching: {source["name"]} ({source["url"]})')
        articles = fetch_rss_feed(source['url'], source['name'])
        
        for article in articles:
            added = add_article(
                title=article['title'],
                summary=article['summary'],
                url=article['url'],
                source=source['name'],
                source_type='rss',
                tier=2,
                published_at=article['published_at']
            )
            if added:
                total_new += 1
        
        update_source_last_fetched(source['id'])
        print(f'  -> {len(articles)} articles found')
    
    print(f'RSS aggregation complete. Total new articles: {total_new}')
    return total_new

if __name__ == '__main__':
    run_rss_aggregator()