"""walkforward.py - run the swarm's rules over past markets.

Tune on one window, score on the next one, roll forward.
Only the untouched windows count toward the scorecard.
"""
import copy
import json
import os
import sys

import setups

COSTS = {"slip_bps": 5, "buy_fee_usd": 0.01,
         "sell_fee_usd": 0.02, "decision_usd": 0.0}
TRAIN, TEST, ACCOUNT = 252, 126, 1000.0
GRID = {"breakout": [10, 20, 40], "pullback": [10, 20, 40],
        "bounce": [2, 3, 4]}


def sell(shares, px, entry, slip, costs, trades, n):
    gross = shares * px
    cash = gross * (1 - slip) - costs["sell_fee_usd"]
    n["cost"] += gross * slip + costs["sell_fee_usd"]
    trades.append(cash / (shares * entry) - 1)
    return cash


def trade(setup, bars, lo, hi, costs=COSTS):
    """Trade one setup over bars[lo:hi]. One position."""
    slip = costs["slip_bps"] / 10000
    flat = costs["buy_fee_usd"] + costs["decision_usd"]
    cash, shares, entry, held = ACCOUNT, 0.0, 0.0, 0
    order, trades, curve = None, [], []
    n = {"signals": 0, "unfilled": 0, "cost": 0.0}
    for i in range(lo, hi):
        b, last = bars[i], i == hi - 1
        if order:                       # yesterday's order
            side, lim = order
            if side == "buy":
                px = b["o"] if b["o"] <= lim else (
                    lim if b["l"] <= lim else None)
            else:
                px = b["o"] if b["o"] >= lim else (
                    lim if b["h"] >= lim else None)
            if px is None:
                n["unfilled"] += 1
            elif side == "buy":
                px *= 1 + slip
                cash -= flat
                shares, entry, held = cash / px, px, 0
                n["cost"] += shares * px * slip + flat
                cash = 0.0
            else:
                cash = sell(shares, px, entry, slip, costs,
                            trades, n)
                shares = 0.0
            order = None
        if shares:
            held += 1
            why = setups.exit_reason(setup, entry, b["c"], held)
            if last:                    # window ends: sell here
                cash = sell(shares, b["c"], entry, slip, costs,
                            trades, n)
                shares = 0.0
            elif why:
                order = ("sell", round(b["c"] * 0.997, 2))
        elif not last and setups.fires(setup, bars, i):
            n["signals"] += 1
            order = ("buy", setups.entry_limit(setup, b["c"]))
        curve.append(cash + shares * b["c"])
    return trades, curve, n


def stats(curve, start=ACCOUNT):
    rets, peak, dd, prev = [], start, 0.0, start
    for v in curve:
        rets.append(v / prev - 1)
        peak = max(peak, v)
        dd = max(dd, 1 - v / peak)
        prev = v
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    daily = mean / var ** 0.5 if var else 0.0
    # yearly Sharpe at a 0% risk-free rate, and its t-statistic
    return (curve[-1] / start - 1, dd, daily * 252 ** 0.5,
            daily * len(rets) ** 0.5)


def walk(base, bars, costs=COSTS):
    """Pick the lookback on each training window, then score
    the next window with it."""
    folds, trades, curve, tot, scale = [], [], [], {}, 1.0
    for lo in range(0, len(bars) - TRAIN - TEST + 1, TEST):
        best, best_end = None, None
        for look in GRID[base["entry"]["type"]]:
            s = copy.deepcopy(base)
            s["entry"]["lookback"] = look
            _, c, _ = trade(s, bars, lo, lo + TRAIN, costs)
            if best_end is None or c[-1] > best_end:
                best, best_end = s, c[-1]
        mid = lo + TRAIN
        t, c, n = trade(best, bars, mid, mid + TEST, costs)
        folds.append({"from": bars[mid]["t"],
                      "lookback": best["entry"]["lookback"],
                      "tuned": best_end / ACCOUNT - 1,
                      "untouched": c[-1] / ACCOUNT - 1})
        trades += t
        curve += [v * scale for v in c]
        for k, v in n.items():
            v = v * scale if k == "cost" else v
            tot[k] = tot.get(k, 0) + v
        scale = curve[-1] / ACCOUNT
    return folds, trades, curve, tot


def scorecard(symbol, bench="BENCH", folder="fixtures",
              costs=COSTS):
    bars = json.load(open(f"{folder}/bars_{symbol}.json"))
    bb = json.load(open(f"{folder}/bars_{bench}.json"))
    bb = {b["t"]: b["c"] for b in bb}   # benchmark close by day
    first = TRAIN
    last = TRAIN + TEST * ((len(bars) - TRAIN) // TEST) - 1
    b_ret = bb[bars[last]["t"]] / bb[bars[first - 1]["t"]] - 1
    cards = []
    for sid, base in setups.load_all().items():
        folds, t, curve, n = walk(base, bars, costs)
        ret, dd, sharpe, t_stat = stats(curve)
        latest, best_end = None, None
        for look in GRID[base["entry"]["type"]]:
            s = copy.deepcopy(base)
            s["entry"]["lookback"] = look
            _, c, _ = trade(s, bars, len(bars) - TRAIN,
                            len(bars), costs)
            if best_end is None or c[-1] > best_end:
                latest, best_end = look, c[-1]
        cards.append({
            "symbol": symbol, "strategy": sid,
            "sha256": base["sha256"], "benchmark": bench,
            "window": [bars[first]["t"], bars[last]["t"]],
            "trades": len(t), "wins": sum(x > 0 for x in t),
            "net_pct": ret, "net_usd": round(ret * ACCOUNT, 2),
            "max_drawdown": dd, "sharpe": sharpe,
            "t_stat": t_stat, "risk_free": 0.0,
            "cost_usd": round(n["cost"], 2),
            "signals": n["signals"], "unfilled": n["unfilled"],
            "benchmark_pct": b_ret,
            "beat": "YES" if ret > b_ret else "no",
            "costs": costs, "folds": folds,
            "latest_lookback": latest})
    cards.sort(key=lambda c: -c["net_pct"])
    return cards


def show(cards):
    c0 = cards[0]
    print(f"{c0['symbol']}: untouched days {c0['window'][0]} "
          f"to {c0['window'][1]}")
    print(f"{c0['benchmark']} buy and hold, same days: "
          f"{c0['benchmark_pct']:+.1%}")
    print("strategy      net trades wins  maxDD sharpe    t "
          " cost$ beat?")
    for c in cards:
        print(f"{c['strategy']:<11}{c['net_pct']:>+7.1%}"
              f"{c['trades']:>6}{c['wins']:>5}"
              f"{c['max_drawdown']:>7.1%}{c['sharpe']:>7.2f}"
              f"{c['t_stat']:>5.1f}{c['cost_usd']:>7.2f} "
              f"{c['beat']}")
    for c in cards:
        print(f"{c['strategy']}: {c['signals']} signals, "
              f"{c['unfilled']} never filled")


def show_folds(card):
    print(f"{card['strategy']} window by window")
    print("untouched from  lookback   tuned  untouched")
    for f in card["folds"]:
        print(f"{f['from']:<16}{f['lookback']:>8}"
              f"{f['tuned']:>+8.1%}{f['untouched']:>+11.1%}")
    print(f"tuned on the latest {TRAIN} days: "
          f"lookback {card['latest_lookback']}")


if __name__ == "__main__":
    symbol = sys.argv[1]
    folder = "bars" if os.path.exists(
        f"bars/bars_{symbol}.json") else "fixtures"
    bench = "SPY" if folder == "bars" else "BENCH"
    cards = scorecard(symbol, bench, folder)
    if len(sys.argv) > 2:
        show_folds(next(c for c in cards
                        if c["strategy"] == sys.argv[2]))
    else:
        show(cards)
        os.makedirs("cards", exist_ok=True)
        with open(f"cards/{symbol}.json", "w") as f:
            json.dump({"cards": cards}, f, indent=1)
        print(f"saved cards/{symbol}.json")
