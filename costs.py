"""costs.py - what one decision costs, and the move that pays it.

Model cost is measured: tokens each seat used, times the rates
you typed into swarm.json. The rest are your assumptions, and
the sheet says which is which.
"""
import json
import sys

import ledger


def model_usd(usage, rates):
    out = {}
    for seat, calls in usage.items():
        usd = 0.0
        for c in calls:
            r = rates.get(c["model"], {"in": 0.0, "out": 0.0})
            usd += c["in"] / 1e6 * r["in"]
            usd += c["out"] / 1e6 * r["out"]
        out[seat] = usd
    return out


def sheet(run, cfg, position_usd=None):
    k = cfg["costs"]
    o = run.get("order")
    pos = position_usd or (o["qty"] * o["limit_price"] if o
                           else 0.0)
    seats = model_usd(run["usage"], cfg["rates"])
    rows = [("model calls", "measured", sum(seats.values())),
            ("market data", "assumed",
             k["data_usd_month"] / k["decisions_month"]),
            ("broker fees", "assumed",
             k["buy_fee_usd"] + k["sell_fee_usd"] if pos
             else 0.0),
            ("spread", "assumed", pos * k["spread_bps"] / 10000),
            ("slippage", "assumed",
             2 * pos * k["slip_bps"] / 10000)]
    total = sum(r[2] for r in rows)
    return {"decision_id": run["decision_id"], "seats": seats,
            "rows": rows, "position_usd": pos,
            "total_usd": total,
            "break_even_pct": total / pos if pos else None}


def show(s):
    print(f"decision {s['decision_id']}  "
          f"position ${s['position_usd']:.2f}")
    for name, kind, usd in s["rows"]:
        print(f"  {name:<12}{kind:<9}${usd:>8.4f}")
        if name == "model calls":
            for seat, usd in s["seats"].items():
                print(f"    {seat:<19}${usd:>8.4f}")
    print(f"  {'total':<21}${s['total_usd']:>8.4f}")
    if s["break_even_pct"] is None:
        print("  no order, so this cost bought no trade")
    else:
        print(f"  break-even move      "
              f"{s['break_even_pct']:>8.2%}")


def lineups(tokens, cfg):
    """Same tokens, different models in the seats."""
    sizes = [100, 250, 500, 1000]
    print("lineup        $/decision  break-even move at")
    print("                          " + "".join(
        f"${s:<7}" for s in sizes))
    for name, seats in cfg["lineups"].items():
        usage = {seat: [{"model": seats[seat], "in": t[0],
                         "out": t[1]}]
                 for seat, t in tokens.items()}
        fake = {"decision_id": name, "usage": usage}
        line = f"{name:<14}"
        for i, size in enumerate(sizes):
            s = sheet(fake, cfg, size)
            if i == 0:
                line += f"${sum(s['seats'].values()):<11.4f}"
            line += f"{s['break_even_pct']:<8.2%}"
        print(line)


if __name__ == "__main__":
    cfg = json.load(open("swarm.json"))
    if sys.argv[1] == "lineups":
        lineups(json.load(open(sys.argv[2])), cfg)
    else:
        run = json.load(open(sys.argv[1]))
        s = sheet(run, cfg)
        show(s)
        if "--record" in sys.argv:
            db = ledger.connect()
            ledger.add_events(db, run["decision_id"], [{
                "event": "cost", "total_usd": s["total_usd"],
                "seats": s["seats"],
                "rows": [list(r) for r in s["rows"]],
                "event_time_utc": run["as_of_utc"],
                "observed_at_utc": run.get("clock_utc")}])
            print("cost row added to the ledger")
