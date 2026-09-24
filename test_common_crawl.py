"""
Quick test: is vat-lookup.co.uk indexed by Common Crawl? Just to confirm the
free CDX API works as documented, before deciding whether bulk search (paid,
via AWS Athena) is worth pursuing further.
"""

import requests

url = "https://index.commoncrawl.org/CC-MAIN-2026-25-index"
params = {"url": "vat-lookup.co.uk", "output": "json"}

res = requests.get(url, params=params, timeout=15)
print(f"Status: {res.status_code}")
print(f"Lungime raspuns: {len(res.text)} caractere")
print(res.text[:1000])