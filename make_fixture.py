"""make_fixture.py - build the DEMO practice files.

DEMO and BENCH are made-up symbols. Every number comes from
the formula below, so your files match the book's exactly.
"""
import json
import os
from datetime import date, timedelta

TREND = [0.0030, -0.0020, 0.0028, -0.0015, 0.0006, 0.0030,
         -0.0022, 0.0026, -0.0010, 0.0032, -0.0018, 0.0030]


def lcg(seed):
    x = seed
    while True:
        x = (x * 1103515245 + 12345) % 2**31
        yield x / 2**31


def make_bars(seed, start, drifts, vol, gap, n=756):
    rnd, px, day, out = lcg(seed), start, date(2021, 1, 4), []
    for i in range(n):
        while day.weekday() > 4:
            day += timedelta(days=1)
        z = sum(next(rnd) for _ in range(4)) - 2.0
        drift = drifts[i * len(drifts) // n]
        g = next(rnd)
        jump = gap * (1 if g > 0.94 else -1 if g < 0.04 else 0)
        o = px * (1 + jump + 0.3 * vol * (next(rnd) - 0.5))
        c = o * (1 + drift + vol * z)
        h = max(o, c) * (1 + 0.4 * vol * next(rnd))
        lo = min(o, c) * (1 - 0.4 * vol * next(rnd))
        v = int(400000 + 600000 * next(rnd))
        out.append({"t": day.isoformat(), "o": round(o, 2),
                    "h": round(h, 2), "l": round(lo, 2),
                    "c": round(c, 2), "v": v})
        px, day = c, day + timedelta(days=1)
    return out


def save(name, data):
    os.makedirs("fixtures", exist_ok=True)
    path = os.path.join("fixtures", name)
    with open(path, "w") as f:
        json.dump(data, f, indent=1)
    print(f"wrote {path}")


if __name__ == "__main__":
    demo = make_bars(66, 40.0, TREND, 0.014, 0.018)
    bench = make_bars(7, 100.0, [0.0005], 0.008, 0.0)
    save("bars_DEMO.json", demo)
    save("bars_BENCH.json", bench)
    second = [dict(b) for b in demo[-30:]]
    second[-3]["c"] = round(second[-3]["c"] + 0.42, 2)
    save("second_DEMO.json", second)
    day = demo[-1]["t"]
    save("news_DEMO.json", [
        {"title": "DEMO raises full-year sales outlook",
         "publisher": "Fixture Wire",
         "published_utc": f"{day}T13:05:00Z",
         "article_url": "https://example.com/demo-outlook"},
        {"title": "DEMO opens second plant ahead of plan",
         "publisher": "Fixture Daily",
         "published_utc": f"{day}T15:40:00Z",
         "article_url": "https://example.com/demo-plant"},
        {"title": "Supplier warns of parts delays into DEMO",
         "publisher": "Fixture Wire",
         "published_utc": f"{day}T19:12:00Z",
         "article_url": "https://example.com/demo-supplier"},
    ])
