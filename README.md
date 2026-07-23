# 🦅 Thorondor

A customizable intelligence sentinel. Currently monitors all things Anduril and Palmer Luckey through his X feed, site scraper and tech RSS sources. It ranks articles by relevance, delivering daily digests via Telegram.
**Fully customizable** — change a few lines of code to watch whoever and whatever you want.
## Features

- **Anduril Full-Site Monitor** — Crawls every page on anduril.com, detects ANY changes (new pages, content updates), reports as Tier 1
- **X Feed Monitor** — Tracks tweets from any number of configured accounts (Tier 1), only new tweets since last update, max 5 per user
- **RSS Aggregator** — 8 tech/defense feeds (Tier 2), auto-disables dead sources after 3 consecutive failures
- **Concise Summaries** — 1-2 sentence factual summaries via Moonshot AI
- **Telegram Delivery** — Single daily digest message, or on-demand via `/digest`

## Monitored Sources (Out of the Box)

| Source | Type | Tier |
|--------|------|------|
| Anduril website | Full-site change detector | 1 |
| Palmer Luckey (@PalmerLuckey) | X API | 1 |
| Isaiah Taylor (@isaiah_p_taylor) | X API | 1 |
| David Kirtley (@Dkirtley) | X API | 1 |
| Billy Thalheimer (@billythalheimer) | X API | 1 |
| Thomas Healy (@ThomasHealyCEO) | X API | 1 |
| MIT Technology Review | RSS | 2 |
| IEEE Spectrum | RSS | 2 |
| Hackaday | RSS | 2 |
| Ars Technica | RSS | 2 |
| TechCrunch | RSS | 2 |
| SpaceX | RSS | 2 |
| 3D Printing Industry | RSS | 2 |
| The Drive - War Zone | RSS | 2 |

## Quick Start

### 1. Clone and setup

```bash
git clone https://github.com/mgreenhough/Thorondor.git
cd Thorondor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:
```env
MOONSHOT_API_KEY=your_moonshot_key_here
MOONSHOT_API_ENDPOINT=https://api.moonshot.ai/v1
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
X_BEARER_TOKEN=your_x_api_bearer_token
```

### 3. Create the database

```bash
sqlite3 thorondor.db < schema.sql
sqlite3 thorondor.db < seed.sql
```

### 4. Run

**Daily digest (one-shot, collects and sends):**
```bash
python3 run_digest.py
```

**Telegram bot (for manual commands):**
```bash
python3 telegram_bot.py
```

**Test commands in Telegram:**
- `/digest` — send latest brief on demand
- `/add <username>` — add X account to monitor
- `/delete <username>` — remove X account
- `/list` — show monitored accounts

## Getting Credentials

### Moonshot AI
1. Go to https://platform.kimi.ai
2. Create an account and top up
3. Generate an API key

### Telegram Bot
1. Message @BotFather on Telegram
2. Send `/newbot`
3. Name it and choose username ending in `bot`
4. Copy the HTTP API token
5. Send a message to your bot
6. Visit `https://api.telegram.org/bot<TOKEN>/getUpdates`
7. Find `"chat":{"id":123456789` — that's your `TELEGRAM_CHAT_ID`

### X API
1. Go to https://developer.x.com
2. Create a project and app
3. Generate a Bearer Token

## Running on a Server

### Daily cron

```bash
crontab -e
```

Add:
```cron
30 4 * * * cd /opt/thorondor && source venv/bin/activate && python3 run_digest.py >> /var/log/thorondor/digest.log 2>&1
```

This runs at 04:30 Adelaide time (19:00 UTC).

### Log rotation

Create `/etc/logrotate.d/thorondor`:
```
/var/log/thorondor/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
```

## Project Structure

| File | Purpose |
|------|---------|
| `telegram_bot.py` | Telegram bot, manual digest and user management commands |
| `run_digest.py` | One-shot daily digest: collects, sends, marks notified, exits |
| `feed_rss.py` | RSS feed aggregator with auto-disable for dead sources |
| `monitor_x.py` | X API monitor, loops all configured users, only new tweets |
| `scraper_anduril.py` | Full-site Anduril change detector |
| `intelligence.py` | Moonshot AI summaries |
| `database.py` | SQLite operations |
| `schema.sql` | Database schema |

## Customization

### Add X accounts

Via Telegram: `/add elonmusk`

Or insert directly:
```sql
INSERT INTO x_users (username, tier) VALUES ('elonmusk', 1);
```

### Add RSS feeds

```sql
INSERT INTO sources (name, url, source_type) VALUES ('Your Feed', 'https://example.com/feed.xml', 'rss');
```

### Change tier ranking

- `tier=1` — Always appears at top of digest (Anduril + X accounts)
- `tier=2` — RSS feeds

## License

MIT