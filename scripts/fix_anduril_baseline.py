import sqlite3
import sys

DB_PATH = '/opt/thorondor/thorondor.db'

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "DELETE FROM articles WHERE source = 'Anduril' AND title LIKE 'Anduril — New page:%'"
    )
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    print(f'Deleted {deleted} baseline Anduril articles')
    return 0

if __name__ == '__main__':
    sys.exit(main())