"""live.py - real bars and news for packet.py.

Source 1: Alpaca daily bars, IEX feed, split-adjusted.
Source 2: Massive daily bars. News: Massive.
Asks only for finished days, so a half-built bar never
leaks into a morning decision.
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import requests
from alpaca.data.enums import Adjustment, DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

import keys

MASSIVE = "https://api.massive.com"


def alpaca_bars(symbol, start, end):
    client = StockHistoricalDataClient(
        os.environ["APCA_API_KEY_ID"],
        os.environ["APCA_API_SECRET_KEY"])
    got = client.get_stock_bars(StockBarsRequest(
        symbol_or_symbols=symbol, timeframe=TimeFrame.Day,
        start=start, end=end, feed=DataFeed.IEX,
        adjustment=Adjustment.SPLIT))
    return [{"t": b.timestamp.date().isoformat(), "o": b.open,
             "h": b.high, "l": b.low, "c": b.close,
             "v": b.volume} for b in got[symbol]]


def massive(path, **params):
    time.sleep(13)                  # free plan: 5 calls a minute
    r = requests.get(
        MASSIVE + path, params=params, timeout=30,
        headers={"Authorization":
                 "Bearer " + os.environ["MASSIVE_API_KEY"]})
    if r.status_code == 429:
        raise SystemExit("Massive: too many calls this minute. "
                         "Wait a minute, then run it again.")
    if r.status_code == 403:
        raise SystemExit("Massive: your plan does not cover "
                         "that date. Ask for an older day.")
    r.raise_for_status()
    return r.json()


def finished_days(days=130):
    """Start and end of the last `days` finished days."""
    end = (datetime.now(timezone.utc) - timedelta(days=1)
           ).replace(hour=23, minute=59, second=0, microsecond=0)
    return end - timedelta(days=days), end


def recent_bars(symbol):
    keys.load()
    return alpaca_bars(symbol, *finished_days())


def fetch(symbol):
    keys.load()
    now = datetime.now(timezone.utc)
    start, end = finished_days()
    bars = alpaca_bars(symbol, start, end)
    agg = massive(
        f"/v2/aggs/ticker/{symbol}/range/1/day/"
        f"{start.date()}/{end.date()}",
        adjusted="true", sort="asc", limit=5000)
    def day(ms):
        return datetime.fromtimestamp(
            ms / 1000, timezone.utc).date().isoformat()

    second = [{"t": day(x["t"]), "c": x["c"], "v": x["v"]}
              for x in agg.get("results", [])][-30:]
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    news = massive("/v2/reference/news", **{
        "ticker": symbol, "published_utc.lte": stamp,
        "order": "desc", "sort": "published_utc", "limit": 3})
    items = [{"title": n["title"],
              "publisher": n["publisher"]["name"],
              "published_utc": n["published_utc"],
              "article_url": n["article_url"]}
             for n in news.get("results", [])]
    return {"as_of": stamp, "now": stamp, "bars": bars[-60:],
            "feed": "iex", "second": second, "news": items,
            "ids": ["alpaca-py", agg.get("request_id"),
                    news.get("request_id")]}


def history(symbol, years=6):
    """Save years of daily bars for the past-markets test."""
    keys.load()
    bars = alpaca_bars(symbol, *finished_days(365 * years))
    os.makedirs("bars", exist_ok=True)
    path = f"bars/bars_{symbol}.json"
    with open(path, "w") as f:
        json.dump(bars, f)
    print(f"{symbol}: {len(bars)} days, {bars[0]['t']} to "
          f"{bars[-1]['t']}, saved {path}")


if __name__ == "__main__":
    for name in sys.argv[1:]:
        history(name)
