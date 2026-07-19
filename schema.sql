CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    summary TEXT,
    url TEXT UNIQUE NOT NULL,
    source TEXT NOT NULL,
    source_type TEXT CHECK(source_type IN ('anduril', 'x_api', 'rss')),
    tier INTEGER DEFAULT 2,
    content_hash TEXT,
    embedding BLOB,
    topics TEXT,
    entities TEXT,
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_notified INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER,
    action TEXT CHECK(action IN ('like', 'dislike', 'open', 'save', 'ignore', 'time_spent')),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES articles(id)
);

CREATE TABLE IF NOT EXISTS interest_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity TEXT UNIQUE NOT NULL,
    topic TEXT,
    weight REAL DEFAULT 0.0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    url TEXT NOT NULL,
    source_type TEXT CHECK(source_type IN ('anduril', 'x_api', 'rss')),
    is_active INTEGER DEFAULT 1,
    last_fetched TIMESTAMP
);