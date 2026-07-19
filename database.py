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

def mark_notified(article_ids):
    conn = get_connection()
    conn.executemany('UPDATE articles SET is_notified = 1 WHERE id = ?', [(i,) for i in article_ids])
    conn.commit()
    conn.close()

def log_interaction(article_id, action):
    conn = get_connection()
    conn.execute('INSERT INTO interactions (article_id, action) VALUES (?, ?)', (article_id, action))
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