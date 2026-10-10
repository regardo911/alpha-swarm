"""packet.py - freeze today's facts for one stock.

Two market sources, one news source, one file. Every fact
carries the source it came from. Agents may only cite facts.
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import setups

MAX_GAP = 0.0025        # two closes this far apart get a FLAG


def sha(data):
    if not isinstance(data, bytes):
        data = json.dumps(data, sort_keys=True).encode()
    return hashlib.sha256(data).hexdigest()


def from_fixture(symbol):
    def load(name):
        return json.load(open(f"fixtures/{name}_{symbol}.json"))
    bars = load("bars")[-60:]
    stamp = bars[-1]["t"] + "T21:00:00Z"
    return {"as_of": stamp, "now": stamp[:-3] + "05Z",
            "bars": bars, "feed": "fixture",
            "second": load("second"), "news": load("news"),
            "ids": ["fixture-1", "fixture-2", "fixture-3"]}


def build(symbol, got):
    bars, second = got["bars"], got["second"]
    last, closes = bars[-1], [b["c"] for b in bars]
    high20 = max(b["h"] for b in bars[-21:-1])
    avg20 = sum(closes[-20:]) / 20
    usd_vol = sum(b["c"] * b["v"] for b in second[-20:]) / 20
    facts = [
        ("F1", f"Last close {last['c']:.2f} on {last['t']}"),
        ("F2", f"Highest high of the prior 20 days "
               f"{high20:.2f}"),
        ("F3", f"5-day change "
               f"{closes[-1] / closes[-6] - 1:+.1%}"),
        ("F4", f"20-day average close {avg20:.2f}"),
    ]
    facts = [{"id": i, "text": t, "source": "market-1"}
             for i, t in facts]
    facts.append({"id": "F5", "source": "market-2",
                  "text": "Average daily dollar volume "
                          f"{usd_vol:,.0f}"})
    flags, by_day = [], {b["t"]: b["c"] for b in bars}
    for b in second:
        mine = by_day.get(b["t"])
        if mine and abs(mine - b["c"]) / mine > MAX_GAP:
            flags.append(f"FLAG sources disagree on {b['t']}: "
                         f"{mine:.2f} vs {b['c']:.2f}")
    same = len(second) - len(flags)
    facts.append({"id": "F6", "source": "market-2",
                  "text": f"Second source matches {same} of "
                          f"{len(second)} closes"})
    for k, flag in enumerate(flags, 1):
        facts.append({"id": f"X{k}", "source": "market-2",
                      "text": flag})
    fired, i = [], len(bars) - 1
    for sid, rule in setups.load_all().items():
        if setups.fires(rule, bars, i):
            fired.append(sid)
            lim = setups.entry_limit(rule, last["c"])
            facts.append({"id": f"S{len(fired)}",
                          "source": "setups.py",
                          "text": f"{sid} fired, entry limit "
                                  f"{lim:.2f}"})
    for k, item in enumerate(got["news"], 1):
        facts.append({"id": f"N{k}",
                      "source": item["article_url"],
                      "text": f"{item['title']} "
                              f"({item['publisher']})"})
    packet = {
        "symbol": symbol, "as_of_utc": got["as_of"],
        "created_at_utc": got["now"],
        "market": [
            {"provider": "market-1", "feed": got["feed"],
             "timestamp_utc": got["as_of"],
             "request_id": got["ids"][0],
             "raw_sha256": sha(bars)},
            {"provider": "market-2", "adjusted": True,
             "timestamp_utc": got["as_of"],
             "request_id": got["ids"][1],
             "raw_sha256": sha(second)}],
        "news": [dict(n, retrieved_at_utc=got["now"],
                      request_id=got["ids"][2],
                      raw_sha256=sha(n)) for n in got["news"]],
        "facts": facts, "flags": flags, "setups_fired": fired,
        "last_close": last["c"], "avg_usd_volume": usd_vol,
    }
    packet["packet_id"] = "P-" + sha(packet)[:10]
    return packet


def save(packet):
    os.makedirs("packets", exist_ok=True)
    path = f"packets/{packet['packet_id']}.json"
    with open(path, "w") as f:
        json.dump(packet, f, indent=1)
    return path


def show(packet, path):
    print(f"{packet['symbol']} as of {packet['as_of_utc']}")
    for fact in packet["facts"]:
        print(f"  {fact['id']:<3} {fact['text']}")
    srcs = sorted({f["source"] for f in packet["facts"]})
    print(f"{len(packet['facts'])} facts, {len(srcs)} sources, "
          f"{len(packet['flags'])} flag(s)")
    print(f"setups fired: {packet['setups_fired'] or 'none'}")
    print(f"saved {path}")


def scan(fixture):
    """Which stocks on the watchlist fired a setup today?"""
    rules = setups.load_all()
    names = json.load(open("swarm.json"))["watchlist"]
    for symbol in ["DEMO"] if fixture else names:
        if fixture:
            bars = from_fixture(symbol)["bars"]
        else:
            import live
            bars = live.recent_bars(symbol)
        hits = [sid for sid, rule in rules.items()
                if setups.fires(rule, bars, len(bars) - 1)]
        print(f"{symbol:<6}{bars[-1]['t']}  close "
              f"{bars[-1]['c']:>8.2f}  "
              f"{', '.join(hits) or 'no setup'}")


if __name__ == "__main__":
    fixture = "--fixture" in sys.argv
    if sys.argv[1] == "scan":
        scan(fixture)
    else:
        symbol = sys.argv[1]
        if fixture:
            got = from_fixture(symbol)
        else:
            import live
            got = live.fetch(symbol)
        packet = build(symbol, got)
        show(packet, save(packet))
