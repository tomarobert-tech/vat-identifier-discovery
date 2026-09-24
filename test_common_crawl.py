"""
Quick test: is vat-lookup.co.uk indexed by Common Crawl? Just to confirm the
free CDX API works as documented, before deciding whether bulk search (paid,
via AWS Athena) is worth pursuing further.

This is the script behind the Common Crawl finding in README.md (Part 1,
source 8): confirmed the free API works (HTTP 200, a real captured page from
12 June 2026), before deciding not to pursue the paid bulk-search route.
"""

import requests

url = "https://index.commoncrawl.org/CC-MAIN-2026-25-index"
params = {"url": "vat-lookup.co.uk", "output": "json"}

res = requests.get(url, params=params, timeout=15)
print(f"Status: {res.status_code}")
print(f"Response length: {len(res.text)} characters")
print(res.text[:1000])