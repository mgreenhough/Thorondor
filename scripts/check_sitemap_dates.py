#!/usr/bin/env python3
import requests
from xml.etree import ElementTree as ET

url = 'https://www.anduril.com/sitemap.xml'
resp = requests.get(url, headers={'User-Agent': 'ThorondorBot/1.0'}, timeout=30)
print(f'Status: {resp.status_code}')
print(f'First 2000 chars:\n{resp.text[:2000]}')