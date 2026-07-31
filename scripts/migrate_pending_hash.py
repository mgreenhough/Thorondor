#!/usr/bin/env python3
import sqlite3
import sys

DB_PATH = '/opt/thorondor/thorondor.db'

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("PRAGMA table_info(page_snapshots)")
    columns = [row[1] for row in cur.fetchall()]
    
    if 'pending_hash' in columns:
        print('pending_hash column already exists')
        return 0
    
    conn.execute('ALTER TABLE page_snapshots ADD COLUMN pending_hash TEXT')
    conn.commit()
    print('Added pending_hash column to page_snapshots')
    return 0

if __name__ == '__main__':
    sys.exit(main())