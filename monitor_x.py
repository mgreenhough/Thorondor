#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import requests
from database import add_article, get_x_users, update_x_user_id, get_connection

load_dotenv()

BEARER_TOKEN = os.getenv('X_BEARER_TOKEN')
HEADERS = {'Authorization': f'Bearer {BEARER_TOKEN}'}


def get_user_id(username):
    url = f'https://api.twitter.com/2/users/by/username/{username}'
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200:
        return r.json()['data']['id']
    print(f'Error getting user ID for {username}: {r.status_code} - {r.text}')
    return None


def get_latest_stored_tweet_id(username):
    """Return the highest tweet ID already in the DB for this user, or None."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT url FROM articles WHERE source = ? AND source_type = 'x_api'",
            (username,)
        ).fetchall()
    finally:
        conn.close()

    max_id = None
    for row in rows:
        parts = row['url'].rstrip('/').split('/')
        if len(parts) >= 2:
            try:
                tweet_id = int(parts[-1])
                if max_id is None or tweet_id > max_id:
                    max_id = tweet_id
            except ValueError:
                continue
    return max_id


def fetch_tweets(user_id, username, max_results=5, since_id=None):
    url = f'https://api.twitter.com/2/users/{user_id}/tweets'
    params = {
        'max_results': max_results,
        'tweet.fields': 'created_at,public_metrics',
        'exclude': 'replies,retweets'
    }
    if since_id:
        params['since_id'] = since_id

    r = requests.get(url, headers=HEADERS, params=params)
    if r.status_code != 200:
        print(f'Error fetching tweets for {username}: {r.status_code} - {r.text}')
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


def process_user(user):
    username = user['username']
    x_user_id = user.get('x_user_id')
    tier = user.get('tier', 1)

    # Resolve user ID if not cached
    if not x_user_id:
        x_user_id = get_user_id(username)
        if not x_user_id:
            print(f'SKIP {username}: could not resolve user ID')
            return 0
        update_x_user_id(username, x_user_id)

    # Only fetch tweets newer than the last one we stored
    since_id = get_latest_stored_tweet_id(username)
    if since_id:
        print(f'Fetching @{username} tweets since ID {since_id}')
    else:
        print(f'No previous tweets for @{username} — fetching latest 5')

    tweets = fetch_tweets(x_user_id, username, max_results=5, since_id=since_id)
    total_new = 0
    for tweet in tweets:
        added = add_article(
            title=tweet['title'],
            summary=tweet['summary'],
            url=tweet['url'],
            source=username,
            source_type='x_api',
            tier=tier,
            published_at=tweet['published_at']
        )
        if added:
            total_new += 1

    print(f'@{username}: {total_new} new tweets (tier {tier})')
    return total_new


def run_x_monitor():
    if not BEARER_TOKEN:
        print('X_BEARER_TOKEN not set')
        return 0

    users = get_x_users(active_only=True)
    if not users:
        print('No X users configured. Use /add <username> to add accounts.')
        return 0

    total_new = 0
    for user in users:
        total_new += process_user(user)

    print(f'X monitor complete. Total new tweets: {total_new}')
    return total_new


if __name__ == '__main__':
    run_x_monitor()