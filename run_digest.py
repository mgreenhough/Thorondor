#!/usr/bin/env python3
import os
import sys

print('=== THORONDOR DAILY DIGEST ===')
print('Running Anduril scraper...')
from scraper_anduril import run_anduril_scraper
anduril_count = run_anduril_scraper()

print('Running X monitor...')
from monitor_x import run_x_monitor
x_count = run_x_monitor()

print('Running RSS aggregator...')
from feed_rss import run_rss_aggregator
rss_count = run_rss_aggregator()

print(f'\nSummary: {anduril_count} Anduril, {x_count} X, {rss_count} RSS')
print('Done. Use /digest in Telegram to send briefing.')