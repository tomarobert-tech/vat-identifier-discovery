"""
The very first, simplest test of DuckDuckGo's HTML search - just one query,
to see what a raw response looks like before building anything more
automated around it. This came before ddg_pipeline.py and
debug_ddg_pipeline.py, which is where the actual 25-company test and the
202-status blocking finding described in README.md (Part 1, source 1) come
from.
"""

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote('British Telecommunications VAT GB')}"
res = requests.get(url, headers=HEADERS, timeout=8)

print(f"Status: {res.status_code}")
print(f"Response length: {len(res.text)} characters")
print(res.text[:2000])