import sqlite3
import sys

DB_PATH = '/opt/thorondor/thorondor.db'

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Find dead sources
    dead = ['Anduril Blog', 'Anthropic Blog']
    for name in dead:
        cur.execute('SELECT COUNT(*) FROM sources WHERE name = ?', (name,))
        count = cur.fetchone()[0]
        if count:
            cur.execute('DELETE FROM articles WHERE source = ?', (name,))
            articles_deleted = cur.rowcount
            cur.execute('DELETE FROM sources WHERE name = ?', (name,))
            print(f'Removed {name}: {articles_deleted} articles, 1 source')
        else:
            print(f'{name}: not found (already clean)')

    conn.commit()
    conn.close()
    print('Cleanup complete')

if __name__ == '__main__':
    main()