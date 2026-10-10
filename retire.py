"""retire.py - continue, revise or retire each strategy.

The thresholds are recorded in the ledger before the results
exist. Change them afterwards and this file refuses to rule.
"""
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone

import ledger

RULES = "stop_rules.json"


def rules_sha():
    return hashlib.sha256(open(RULES, "rb").read()).hexdigest()


def lock(db):
    """Record today's thresholds. Results come after this."""
    now = datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    body = {"sha256": rules_sha(), "locked_utc": now,
            "rules": json.load(open(RULES))}
    try:
        ledger.record(db, "RULES", "rule_set", "human", body,
                      None, now)
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()           # locked twice in one second
    print(f"thresholds locked {rules_sha()[:12]}")


def rule(r, trades, net_usd, drawdown_pct, beat):
    """One result in, exactly one verdict out."""
    if trades < r["min_trades"]:
        need = r["min_trades"]
        return "KEEP RUNNING", f"{trades} of {need} trades"
    if net_usd < r["retire_if_net_usd_below"]:
        return "RETIRE", f"net ${net_usd:.2f}"
    if drawdown_pct > r["retire_if_drawdown_pct_above"]:
        return "RETIRE", f"drawdown {drawdown_pct:.1f}%"
    if r["revise_if_behind_benchmark"] and beat == "no":
        return "REVISE", "made money, lost to the benchmark"
    return "CONTINUE", "passed every threshold"


def decide(db):
    held = ledger.last_lock(db)
    if not held:
        raise SystemExit("no thresholds locked. Run: "
                         "python retire.py lock")
    lock_id, body, lock_row = held
    locked = json.loads(body)
    if rules_sha() != locked["sha256"]:
        print(f"REFUSED: {RULES} changed after it was locked")
        print(f"  locked  {locked['sha256'][:12]}")
        print(f"  on disk {rules_sha()[:12]}")
        print("  put the file back, or lock the new one and "
              "rerun the test")
        raise SystemExit(1)
    cards = db.execute(
        "SELECT payload_json FROM decision_events WHERE "
        "event_type = 'test_card' AND parent_event_id = ? "
        "ORDER BY rowid", (lock_id,)).fetchall()
    if not cards:
        print("no results under this lock yet. Run the test, "
              "then add the cards")
    for (card,) in cards:
        c = json.loads(card)
        verdict, why = rule(
            locked["rules"], c["trades"], c["net_usd"],
            100 * c["max_drawdown"], c["beat"])
        print(f"{c['strategy']:<12}{c['symbol']:<6}"
              f"{verdict:<13}{why}")
        try:
            ledger.record(
                db, f"T-{c['symbol']}", "review", "human",
                {"strategy": c["strategy"], "verdict": verdict,
                 "why": why}, lock_id, locked["locked_utc"])
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()       # this verdict is already in
    yours(db, locked["rules"], lock_row)


def yours(db, rules, lock_row):
    """The same rule, on your own trades since the lock."""
    cap = json.load(open("mandate.json"))["cap_usd"]
    by_strategy = {}
    for t in ledger.closed_trades(db).values():
        if t["feed"] != "fixture" and t["row"] > lock_row:
            by_strategy.setdefault(t["strategy"], []).append(
                t["net"])
    for strategy, nets in by_strategy.items():
        total = peak = drop = 0.0
        for net in nets:
            total += net
            peak = max(peak, total)
            drop = max(drop, peak - total)
        verdict, why = rule(rules, len(nets), total,
                            100 * drop / cap, "YES")
        print(f"{strategy:<12}{'yours':<6}{verdict:<13}{why}")


if __name__ == "__main__":
    db = ledger.connect()
    if sys.argv[1:] == ["lock"]:
        lock(db)
    else:
        decide(db)
