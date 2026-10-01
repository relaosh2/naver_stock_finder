import sys
import requests

sys.stdout.reconfigure(encoding='utf-8')

endpoints = [
    "short-sale", "short_sale", "shortSale",
    "short-trade", "short_trade", "shortTrade",
    "short-selling", "short_selling", "shortSelling",
    "short-balance", "short_balance", "shortBalance",
    "short-info", "short_info", "shortInfo",
    "short-status", "short_status", "shortStatus",
    "short-summary", "short_summary", "shortSummary",
    "short-history", "short_history", "shortHistory",
    "short-trend", "short_trend", "shortTrend",
    "short-rate", "short_rate", "shortRate",
    "short", "shortsale", "shorttrade", "shortbalance"
]

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for ep in endpoints:
    url = f"https://m.stock.naver.com/api/stock/005930/{ep}"
    res = requests.get(url, headers=headers)
    if res.status_code != 404:
        print(f"FOUND!! ({res.status_code}): {url}")
        print(res.text[:200])
