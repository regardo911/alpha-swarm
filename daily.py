"""daily.py - the swarm's working day.

morning  before the open: the record, exits, then new ideas
check    any time: where is every order
week     the weekly review: scoreboard, ladder, stop rules
"""
import glob
import json
import os
import sqlite3
import sys

import broker
import costs
import ladder
import ledger
import live
import packet
import retire
import setups
import swarm


def finish(db, kind, lines):
    """Write the sheet and leave one row in the ledger."""
    stamp = broker.now()
    os.makedirs("sheets", exist_ok=True)
    with open(f"sheets/{stamp[:10]}-{kind}.txt", "w") as f:
        f.write("\n".join(lines) + "\n")
    try:
        ledger.record(db, f"DAY-{stamp[:10]}", kind, "execution",
                      {"lines": lines}, None, stamp)
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()           # same run, same second: one row
    print("\n".join(lines))


def sync(db):
    """Ask the broker about every order sent so far. Fills go
    into the ledger. Returns the lines for the sheet and the
    stocks with a buy still waiting."""
    lines, waiting = [], set()
    for path in sorted(glob.glob("orders/D-*.json")):
        did = json.load(open(path))["decision_id"]
        events = json.load(open(broker.check(did)))["events"]
        try:
            n = ledger.add_events(db, did, events)
        except SystemExit:      # sent by hand, never loaded
            ledger.add_run(db, json.load(
                open(f"runs/{did}.json")))
            n = ledger.add_events(db, did, events)
        lines.append(f"{did}: {n} new row(s)")
        done = {e.get("broker_order_id") for e in events
                if e["event"] not in ("submitted",
                                      "partial_fill")}
        waiting |= {e["symbol"] for e in events
                    if e["event"] == "submitted"
                    and e["side"] == "buy"
                    and e["broker_order_id"] not in done}
    return lines, waiting


def morning():
    cfg = json.load(open("swarm.json"))
    client, _ = broker.connect()
    db, rules = ledger.connect(), setups.load_all()
    # a retired rule still owns the exits of trades it opened
    exits = dict(setups.load_all("strategies/retired"), **rules)
    clock = client.get_clock()
    lines = [f"morning run {broker.now()}"]
    today = clock.timestamp.date()
    if not clock.is_open and clock.next_open.date() != today:
        lines.append("market closed today, next open "
                     f"{clock.next_open}")
        return finish(db, "morning", lines)
    _, queued = sync(db)                    # the record first
    held = ledger.open_trades(db)
    for symbol, t in held.items():          # then exits
        bars = live.recent_bars(symbol)
        days = sum(1 for b in bars
                   if b["t"] >= t["entry_day"])
        why = setups.exit_reason(exits[t["strategy"]],
                                 t["entry_px"], bars[-1]["c"],
                                 days)
        if not why:
            lines.append(f"{symbol}: hold, day {days}")
            continue
        run = json.load(open(f"runs/{t['decision_id']}.json"))
        tag = f"-x{today:%m%d}"
        _, got = broker.send(run, "sell", t["qty"],
                             bars[-1]["c"] * 0.997, tag)
        lines.append(f"{symbol}: SELL sent ({why}), "
                     f"{got['status'] if got else 'refused'}")
    busy = set(held) | queued
    room = cfg["limits"]["max_open_positions"] - len(busy)
    if "rates" not in cfg or "costs" not in cfg:
        lines.append("no new ideas: swarm.json has no rates "
                     "and costs blocks (Chapter 9)")
        room = 0
    for symbol in cfg["watchlist"]:         # then new ideas
        if symbol in queued:
            lines.append(f"{symbol}: buy already waiting")
        if symbol in busy or room <= 0:
            continue
        bars = live.recent_bars(symbol)
        last = len(bars) - 1
        if not any(setups.fires(r, bars, last)
                   for r in rules.values()):
            lines.append(f"{symbol}: no setup")
            continue
        path = packet.save(packet.build(symbol,
                                        live.fetch(symbol)))
        run = swarm.main(path, open_positions=len(busy))
        ledger.add_run(db, run)
        bill = costs.sheet(run, cfg)        # price the decision
        ledger.add_events(db, run["decision_id"], [{
            "event": "cost", "total_usd": bill["total_usd"],
            "seats": bill["seats"],
            "rows": [list(r) for r in bill["rows"]],
            "event_time_utc": run["as_of_utc"],
            "observed_at_utc": run.get("clock_utc")}])
        note = run["status"]
        if run["status"] == "RISK_APPROVED":
            saved, got = broker.send(run)
            ledger.add_events(db, run["decision_id"],
                              json.load(open(saved))["events"])
            note += ", order " + (got["status"] if got
                                  else "refused")
            room -= 1
        lines.append(f"{symbol}: {note} ({run['decision_id']})")
    finish(db, "morning", lines)


def check():
    db = ledger.connect()
    lines, _ = sync(db)
    finish(db, "check", [f"check {broker.now()}"] + lines)


def week():
    db = ledger.connect()
    ledger.score(db)
    print()
    ladder.main([])
    print()
    try:
        retire.decide(db)
    except SystemExit as stop:
        print(stop)


if __name__ == "__main__":
    {"morning": morning, "check": check, "week": week}[
        sys.argv[1]]()
