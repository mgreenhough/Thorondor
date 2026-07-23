import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'thorondor.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def add_article(title, summary, url, source, source_type, tier=2, content_hash=None, topics=None, entities=None, published_at=None):
    conn = get_connection()
    try:
        conn.execute('''
            INSERT OR IGNORE INTO articles (title, summary, url, source, source_type, tier, content_hash, topics, entities, published_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, summary, url, source, source_type, tier, content_hash, topics, entities, published_at))
        conn.commit()
        return True
    except Exception as e:
        print(f'Error adding article: {e}')
        return False
    finally:
        conn.close()

def get_unnotified_articles(tier=None, limit=10):
    conn = get_connection()
    query = 'SELECT * FROM articles WHERE is_notified = 0'
    params = []
    if tier:
        query += ' AND tier = ?'
        params.append(tier)
    query += ' ORDER BY created_at DESC LIMIT ?'
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_unnotified_articles_by_source(source_name, limit=1):
    conn = get_connection()
    rows = conn.execute(
        'SELECT * FROM articles WHERE is_notified = 0 AND source = ? ORDER BY created_at DESC LIMIT ?',
        (source_name, limit)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_most_recent_article_by_source(source_name):
    """Return the single most recent article for a source, regardless of is_notified."""
    conn = get_connection()
    row = conn.execute(
        'SELECT * FROM articles WHERE source = ? ORDER BY created_at DESC LIMIT 1',
        (source_name,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def mark_notified(article_ids):
    conn = get_connection()
    conn.executemany('UPDATE articles SET is_notified = 1 WHERE id = ?', [(i,) for i in article_ids])
    conn.commit()
    conn.close()

def get_sources(source_type=None, active_only=True):
    conn = get_connection()
    query = 'SELECT * FROM sources WHERE 1=1'
    params = []
    if source_type:
        query += ' AND source_type = ?'
        params.append(source_type)
    if active_only:
        query += ' AND is_active = 1'
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_source_last_fetched(source_id):
    conn = get_connection()
    conn.execute('UPDATE sources SET last_fetched = ? WHERE id = ?', (datetime.now(), source_id))
    conn.commit()
    conn.close()


def get_page_snapshot(url):
    conn = get_connection()
    row = conn.execute(
        'SELECT content_hash, text_preview FROM page_snapshots WHERE url = ?',
        (url,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_page_snapshot(url, domain, content_hash, text_preview):
    conn = get_connection()
    now = datetime.now()
    conn.execute('''
        INSERT INTO page_snapshots (url, domain, content_hash, text_preview, first_seen, last_seen)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET
            content_hash = excluded.content_hash,
            text_preview = excluded.text_preview,
            last_seen = excluded.last_seen
    ''', (url, domain, content_hash, text_preview, now, now))
    conn.commit()
    conn.close()


def disable_source(source_id):
    conn = get_connection()
    conn.execute('UPDATE sources SET is_active = 0 WHERE id = ?', (source_id,))
    conn.commit()
    conn.close()


def get_x_users(active_only=True):
    conn = get_connection()
    query = 'SELECT * FROM x_users WHERE 1=1'
    params = []
    if active_only:
        query += ' AND is_active = 1'
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def add_x_user(username, tier=1):
    conn = get_connection()
    try:
        conn.execute(
            'INSERT OR IGNORE INTO x_users (username, tier) VALUES (?, ?)',
            (username.lstrip('@'), tier)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f'Error adding X user: {e}')
        return False
    finally:
        conn.close()


def delete_x_user(username):
    conn = get_connection()
    conn.execute(
        'UPDATE x_users SET is_active = 0 WHERE username = ?',
        (username.lstrip('@'),)
    )
    conn.commit()
    conn.close()


def update_x_user_id(username, x_user_id):
    conn = get_connection()
    conn.execute(
        'UPDATE x_users SET x_user_id = ? WHERE username = ?',
        (x_user_id, username.lstrip('@'))
    )
    conn.commit()
    conn.close()