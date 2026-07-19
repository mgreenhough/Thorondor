# 🦅 Thorondor

Aefense-tech intelligence sentinel. Monitors Anduril, Palmer Luckey's X feed, and tech RSS sources. Ranks articles by relevance using Moonshot embeddings, delivers daily digests via Telegram with 👍/👎 feedback loop.

**Fully customizable** — change a few lines of code to watch whoever and whatever you want.

## Features

- **Tier 1 Sources** — Anduril blog + Palmer Luckey X feed (always top priority)
- **Tier 2 RSS** — 10 tech/defense feeds (ranked by Moonshot relevance)
- **Smart Summaries** — "Why should I care?" context via Moonshot API
- **Telegram Delivery** — Daily digest with inline feedback buttons
- **Self-Learning** — Interest profile builds from your 👍/👎 clicks

## Who Can You Watch?

Everything is configurable. Out of the box it tracks:

| Source | Type | How to Change |
|--------|------|---------------|
| Anduril Blog | Web scraper | Edit `scraper_anduril.py` — change `BASE_URL` |
| Palmer Luckey | X API | Edit `monitor_x.py` — change `PalmerLuckey` username |
| 10 Tech RSS Feeds | RSS | Edit `schema.sql` or insert into `sources` table |

**Add any X account:** Change `'PalmerLuckey'` to any username in `monitor_x.py`.
**Add any RSS feed:** Insert into the `sources` table with `source_type='rss'`.
**Add any website:** Write a scraper module like `scraper_anduril.py` and import it in `run_digest.py`.

## Quick Start

### 1. Clone and setup

```bash
git clone https://github.com/mgreenhough/Thorondor.git
cd Thorondor
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and fill in your credentials:

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
```

### 4. Seed RSS sources (optional)

The database already includes default feeds. To customize, edit `schema.sql` or use SQLite directly.

### 5. Run

**Collect articles manually:**
```bash
python3 run_digest.py
```

**Start the Telegram bot:**
```bash
python3 telegram_bot.py
```

**Send a test digest:**
Message your bot `/digest` on Telegram.

## Getting Credentials

### Moonshot AI
1. Go to https://platform.kimi.ai
2. Create an account and top up
3. Generate an API key
4. Copy to `MOONSHOT_API_KEY`

### Telegram Bot
1. Message @BotFather on Telegram
2. Send `/newbot`
3. Name it and choose username ending in `bot`
4. Copy the HTTP API token to `TELEGRAM_BOT_TOKEN`
5. Send a message to your bot
6. Visit `https://api.telegram.org/bot<TOKEN>/getUpdates`
7. Find `"chat":{"id":123456789` — that's your `TELEGRAM_CHAT_ID`

### X API
1. Go to https://developer.x.com
2. Create a project and app
3. Generate a Bearer Token
4. Copy to `X_BEARER_TOKEN`

## Running on a Server

### Systemd service

Create `/etc/systemd/system/thorondor.service`:

```ini
[Unit]
Description=Thorondor Watcher Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/thorondor
EnvironmentFile=/opt/thorondor/.env
ExecStart=/opt/thorondor/venv/bin/python /opt/thorondor/telegram_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
systemctl enable thorondor
systemctl start thorondor
```

### Daily cron

```bash
crontab -e
```

Add:
```cron
0 19 * * * cd /opt/thorondor && source venv/bin/activate && python3 run_digest.py
```

This runs at 19:00 UTC = 04:30 Adelaide time.

## Project Structure

| File | Purpose |
|------|---------|
| `telegram_bot.py` | Telegram bot, digest delivery, feedback handlers |
| `run_digest.py` | Orchestrates all collectors |
| `feed_rss.py` | RSS feed aggregator |
| `monitor_x.py` | X API monitor for Palmer Luckey |
| `scraper_anduril.py` | Anduril blog scraper |
| `intelligence.py` | Moonshot AI embeddings and summaries |
| `database.py` | SQLite database operations |
| `schema.sql` | Database schema |

## Customization

### Add RSS feeds
Edit `schema.sql` or insert directly:

```sql
INSERT INTO sources (name, url, source_type) VALUES
('Your Feed', 'https://example.com/feed.xml', 'rss');
```

### Change tier ranking
Edit `database.py` or the collector scripts:
- `tier=1` — Always appears at top of digest
- `tier=2` — Ranked by AI relevance

### Add more X accounts
Edit `monitor_x.py` and add more `get_user_id()` / `fetch_tweets()` calls.

## License

MIT