"""ladder.py - has the swarm earned more money yet?

Reads the ledger, checks every gate, prints what is still
missing. It never moves the money. You do, in mandate.json.
"""
import json
import sys
from datetime import datetime, timezone

import ledger


def record_stats(nets, cap):
    """Stats for one rung from a list of net $ per trade."""
    equity, peak, dd = 0.0, 0.0, 0.0
    for n in nets:
        equity += n
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    count = len(nets)
    return {"closed_trades": count,
            "net_per_trade_usd": equity / count if count else 0,
            "drawdown_pct": 100 * dd / cap}


def signed_at(db, mandate):
    """The ledger row where this signature was first seen.
    A new signature starts a new count."""
    last = db.execute(
        "SELECT rowid, event_id, payload_json FROM "
        "decision_events WHERE event_type = 'mandate' "
        "ORDER BY rowid DESC LIMIT 1").fetchone()
    body = json.dumps(mandate, sort_keys=True)
    if last and last[2] == body:
        return last[0]
    now = datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    ledger.record(db, "MANDATE", "mandate", "human", mandate,
                  last[1] if last else None, now)
    db.commit()
    return db.execute("SELECT MAX(rowid) FROM "
                      "decision_events").fetchone()[0]


def check(stats, extra, gates):
    rows = [
        ("closed trades", stats["closed_trades"],
         f">= {gates['closed_trades']}",
         stats["closed_trades"] >= gates["closed_trades"]),
        ("net $ per trade", round(stats["net_per_trade_usd"], 2),
         f">= {gates['min_net_per_trade_usd']}",
         stats["net_per_trade_usd"]
         >= gates["min_net_per_trade_usd"]),
        ("drawdown %", round(stats["drawdown_pct"], 1),
         f"<= {gates['max_drawdown_pct']}",
         stats["drawdown_pct"] <= gates["max_drawdown_pct"]),
        ("unfilled %", extra["unfilled_pct"],
         f"<= {gates['max_unfilled_pct']}",
         extra["unfilled_pct"] <= gates["max_unfilled_pct"]),
        ("order % of volume", extra["order_pct_of_volume"],
         f"<= {gates['max_order_pct_of_daily_volume']}",
         extra["order_pct_of_volume"]
         <= gates["max_order_pct_of_daily_volume"]),
        ("ledger hashes", extra["broken_rows"], "== 0",
         extra["broken_rows"] == 0),
    ]
    return rows


def report(rung, nxt, rows):
    print(f"rung: {rung['name']} "
          f"(${rung['cap_usd']} a trade, {rung['mode']})")
    print("gate               have      need       ")
    for name, have, need, ok in rows:
        print(f"{name:<19}{have!s:<10}{need:<11}"
              f"{'pass' if ok else 'NOT YET'}")
    if nxt is None:
        print("top of the ladder")
    elif all(r[3] for r in rows):
        print(f"EARNED: {nxt['name']}, ${nxt['cap_usd']} a "
              f"trade, {nxt['mode']}")
        print("to take it, you sign mandate.json")
    else:
        short = [r[0] for r in rows if not r[3]]
        print(f"STAY. Still open: {', '.join(short)}")


def main(args):
    ladder = json.load(open("ladder.json"))
    mandate = json.load(open("mandate.json"))
    rungs = ladder["rungs"]
    at = next(i for i, r in enumerate(rungs)
              if r["mode"] == mandate["mode"]
              and r["cap_usd"] == mandate["cap_usd"])
    nxt = rungs[at + 1] if at + 1 < len(rungs) else None
    if args:                            # a what-if record
        what_if = json.load(open(args[0]))
        nets, extra = what_if["nets"], what_if["extra"]
        print(f"WHAT IF: {args[0]}")
    else:
        db = ledger.connect()
        since = signed_at(db, mandate)
        trades = [t for t in ledger.closed_trades(db).values()
                  if t["feed"] != "fixture" and t["row"] > since]
        nets = [t["net"] for t in trades]
        extra = ledger.exec_stats(db, since)
    stats = record_stats(nets, rungs[at]["cap_usd"])
    report(rungs[at], nxt, check(stats, extra, ladder["gates"]))


if __name__ == "__main__":
    main(sys.argv[1:])
