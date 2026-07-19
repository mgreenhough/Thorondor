#!/usr/bin/env python3
import os
import requests
from database import add_article

BEARER_TOKEN = os.getenv('X_BEARER_TOKEN')
HEADERS = {'Authorization': f'Bearer {BEARER_TOKEN}'}

def get_user_id(username):
    url = f'https://api.twitter.com/2/users/by/username/{username}'
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200:
        return r.json()['data']['id']
    print(f'Error getting user ID: {r.status_code} - {r.text}')
    return None

def fetch_tweets(user_id, username, max_results=10):
    url = f'https://api.twitter.com/2/users/{user_id}/tweets'
    params = {
        'max_results': max_results,
        'tweet.fields': 'created_at,public_metrics',
        'exclude': 'replies,retweets'
    }
    r = requests.get(url, headers=HEADERS, params=params)
    if r.status_code != 200:
        print(f'Error fetching tweets: {r.status_code} - {r.text}')
        return []
    
    tweets = r.json().get('data', [])
    articles = []
    for tweet in tweets:
        tweet_url = f'https://x.com/{username}/status/{tweet["id"]}'
        articles.append({
            'title': f'@{username}: {tweet["text"][:100]}...',
            'url': tweet_url,
            'summary': tweet['text'],
            'published_at': tweet.get('created_at')
        })
    return articles

def run_x_monitor():
    if not BEARER_TOKEN:
        print('X_BEARER_TOKEN not set')
        return 0
    
    palmer_id = get_user_id('PalmerLuckey')
    if not palmer_id:
        return 0
    
    tweets = fetch_tweets(palmer_id, 'PalmerLuckey')
    total_new = 0
    for tweet in tweets:
        added = add_article(
            title=tweet['title'],
            summary=tweet['summary'],
            url=tweet['url'],
            source='PalmerLuckey',
            source_type='x_api',
            tier=1,
            published_at=tweet['published_at']
        )
        if added:
            total_new += 1
    
    print(f'X monitor complete. New Palmer tweets: {total_new}')
    return total_new

if __name__ == '__main__':
    run_x_monitor()