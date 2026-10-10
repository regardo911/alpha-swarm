"""setups.py - the swarm's entry and exit rules.

One copy of each rule. The morning run and the past-markets
run both import this file, so they trade the same rules.
"""
import glob
import hashlib
import json


def load_all(folder="strategies"):
    out = {}
    for path in sorted(glob.glob(f"{folder}/*.json")):
        raw = open(path, "rb").read()
        s = json.loads(raw)
        s["id"] = f"{s['name']}-v{s['version']}"
        s["sha256"] = hashlib.sha256(raw).hexdigest()[:12]
        out[s["id"]] = s
    return out


def fires(setup, bars, i):
    """True when the entry rule fires on the close of bar i."""
    e = setup["entry"]
    n = e["lookback"]
    if i < n + 5:
        return False
    c = bars[i]["c"]
    if e["type"] == "breakout":
        return c > max(b["h"] for b in bars[i - n:i])
    if e["type"] == "pullback":
        ma = sum(b["c"] for b in bars[i - n + 1:i + 1]) / n
        old = sum(b["c"] for b in bars[i - n - 4:i - 4]) / n
        return ma > old and 0 <= c / ma - 1 <= e["band_pct"]
    if e["type"] == "bounce":
        days = range(i - n + 1, i + 1)
        return all(bars[j]["c"] < bars[j - 1]["c"] for j in days)
    raise ValueError(f"unknown entry type {e['type']}")


def entry_limit(setup, close):
    return round(close * (1 + setup["limit_pad_pct"]), 2)


def exit_reason(setup, entry_px, close, days_held):
    """Why to sell at this close, or None to keep holding."""
    x = setup["exit"]
    if close <= entry_px * (1 - x["stop_pct"]):
        return "stop"
    if close >= entry_px * (1 + x["target_pct"]):
        return "target"
    if days_held >= x["max_days"]:
        return "time"
    return None
