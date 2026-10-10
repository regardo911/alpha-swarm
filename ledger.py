"""ledger.py - the swarm's append-only record and scoreboard.

Every step of every decision is one row. Rows are never
edited. A fix is a new row that points at the old one.
"""
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone

import setups

DB = "ledger.db"
SCHEMA = """
CREATE TABLE IF NOT EXISTS decision_events (
  event_id TEXT PRIMARY KEY,
  decision_id TEXT NOT NULL,
  parent_event_id TEXT,
  correction_of TEXT,
  event_type TEXT NOT NULL,
  event_time_utc TEXT NOT NULL,
  observed_at_utc TEXT NOT NULL,
  strategy_version TEXT NOT NULL,
  prompt_version TEXT,
  model_id TEXT,
  role TEXT NOT NULL,
  source_packet_id TEXT,
  broker_order_id TEXT,
  payload_json TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS no_update
BEFORE UPDATE ON decision_events
BEGIN SELECT RAISE(ABORT, 'append-only: no UPDATE'); END;
CREATE TRIGGER IF NOT EXISTS no_delete
BEFORE DELETE ON decision_events
BEGIN SELECT RAISE(ABORT, 'append-only: no DELETE'); END;
"""


def connect(path=DB):
    db = sqlite3.connect(path)
    db.execute("PRAGMA recursive_triggers = ON")
    db.executescript(SCHEMA)
    return db


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def record(db, did, kind, role, payload, parent, when,
           seen=None, **cols):
    body = json.dumps(payload, sort_keys=True)
    p_sha = digest(body)
    eid = digest(f"{parent}|{kind}|{p_sha}")[:16]
    seen = seen or datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    row = {"event_id": eid, "decision_id": did,
           "parent_event_id": parent, "event_type": kind,
           "event_time_utc": when, "observed_at_utc": seen,
           "role": role, "payload_json": body,
           "payload_sha256": p_sha, "strategy_version": "none"}
    row.update(cols)
    names = ", ".join(row)
    marks = ", ".join("?" for _ in row)
    db.execute(f"INSERT INTO decision_events ({names}) "
               f"VALUES ({marks})", list(row.values()))
    return eid


def add_run(db, run):
    """One run file becomes one chain of rows."""
    did, when = run["decision_id"], run["as_of_utc"]
    seen = run.get("clock_utc")
    s = run.get("setup")
    cols = {"source_packet_id": run["packet_id"],
            "strategy_version":
                f"{s['id']}@{s['sha256']}" if s else "none"}
    steps = [("evidence", "research",
              {"packet_id": run["packet_id"],
               "feed": run["feed"]})]
    for kind, role in (("brief", "research"),
                       ("first_thesis", "thesis"),
                       ("first_challenge", "challenge"),
                       ("thesis", "thesis"),
                       ("challenge", "challenge"),
                       ("risk", "risk")):
        if kind in run:
            steps.append((kind, role, run[kind]))
    steps.append(("decision", "execution", {
        "status": run["status"], "order": run.get("order"),
        "why": run.get("why") or run.get("error")}))
    parent = None
    for kind, role, payload in steps:
        use = (run["usage"].get(role) or [{}])[-1]
        parent = record(db, did, kind, role, payload, parent,
                        when, seen, model_id=use.get("model"),
                        prompt_version=use.get("card"), **cols)
    db.commit()
    return len(steps)


def add_events(db, did, events):
    """Broker events and cost rows. Skips rows already in."""
    head = db.execute(
        "SELECT event_id, strategy_version, source_packet_id "
        "FROM decision_events WHERE decision_id = ? "
        "ORDER BY rowid DESC LIMIT 1", (did,)).fetchone()
    if not head:
        raise SystemExit(f"{did}: record the run first")
    parent, added = head[0], 0
    for ev in events:
        body = json.dumps(ev, sort_keys=True)
        if db.execute("SELECT 1 FROM decision_events WHERE "
                      "decision_id = ? AND payload_sha256 = ?",
                      (did, digest(body))).fetchone():
            continue
        parent = record(
            db, did, ev["event"], "execution", ev, parent,
            ev["event_time_utc"], ev.get("observed_at_utc"),
            strategy_version=head[1], source_packet_id=head[2],
            broker_order_id=ev.get("broker_order_id"))
        added += 1
    db.commit()
    return added


def open_trades(db):
    """Bought and not yet sold: symbol -> entry details."""
    held = {}
    rows = db.execute(
        "SELECT decision_id, strategy_version, event_time_utc, "
        "payload_json FROM decision_events WHERE event_type "
        "IN ('fill', 'partial_fill') ORDER BY rowid")
    for did, strat, when, body in rows:
        p = json.loads(body)
        t = held.setdefault(p["symbol"], {
            "decision_id": did, "qty": 0.0,
            "strategy": strat.split("@")[0],
            "entry_px": p["price"], "entry_day": when[:10]})
        t["qty"] += p["qty"] if p["side"] == "buy" else -p["qty"]
        if abs(t["qty"]) < 1e-9:    # sold: the next buy is new
            del held[p["symbol"]]
    return {s: t for s, t in held.items() if t["qty"] > 1e-9}


def verify(db):
    """Recompute every hash. Return the ids that do not match."""
    rows = db.execute(
        "SELECT event_id, parent_event_id, event_type, "
        "payload_json, payload_sha256 "
        "FROM decision_events").fetchall()
    ids = {r[0] for r in rows}
    bad = []
    for eid, parent, kind, body, p_sha in rows:
        mine = digest(f"{parent}|{kind}|{p_sha}")[:16]
        if (digest(body) != p_sha or mine != eid
                or (parent and parent not in ids)):
            bad.append(eid)
    return bad


def trace(db, did):
    rows = db.execute(
        "SELECT event_type, role, model_id, strategy_version, "
        "event_id, payload_json FROM decision_events "
        "WHERE decision_id = ? ORDER BY rowid",
        (did,)).fetchall()
    print(f"{did}: {len(rows)} rows")
    for n, (kind, role, model, strat, eid, body) in enumerate(
            rows, 1):
        p = json.loads(body)
        note = (p.get("status") or p.get("verdict")
                or p.get("vote") or p.get("packet_id") or "")
        if "price" in p:
            note = f"{p['side']} {p['qty']} at {p['price']:.2f}"
        elif "limit_price" in p:
            note = f"{p['side']} limit {p['limit_price']:.2f}"
        elif isinstance(p.get("limit"), (int, float)):
            note = f"limit {p['limit']:.2f}"
        elif "total_usd" in p:
            note = f"${p['total_usd']:.4f}"
        print(f" {n:>2} {kind:<13}{role:<10}{eid}  {note}")
    if rows:
        print(f"strategy {rows[0][3]}")
    return rows


def closed_trades(db):
    """Pair buy fills with sell fills, per decision."""
    fills, feeds = {}, {}
    rows = db.execute(
        "SELECT decision_id, strategy_version, event_type, "
        "payload_json, rowid FROM decision_events WHERE "
        "event_type IN ('evidence', 'fill', 'partial_fill', "
        "'cost') ORDER BY rowid")
    for did, strat, kind, body, row in rows:
        p = json.loads(body)
        if kind == "evidence":
            feeds[did] = p.get("feed")
            continue
        t = fills.setdefault(did, {
            "strategy": strat.split("@")[0], "buy": 0.0,
            "sell": 0.0, "qty": 0.0, "cost": 0.0,
            "feed": feeds.get(did), "row": None})
        if kind == "cost":
            t["cost"] += p["total_usd"]
        elif p["side"] == "buy":
            t["buy"] += p["qty"] * p["price"]
            t["qty"] += p["qty"]
            t["row"] = t["row"] or row  # dated by its first buy
        else:
            t["sell"] += p["qty"] * p["price"]
            t["qty"] -= p["qty"]
    for t in fills.values():
        t["net"] = t["sell"] - t["buy"] - t["cost"]
    return {d: t for d, t in fills.items()
            if t["sell"] and abs(t["qty"]) < 1e-9}


def board(trades, title):
    rows = {}
    for t in trades:
        r = rows.setdefault(t["strategy"], [0, 0, 0.0])
        r[0] += 1
        r[1] += t["net"] > 0
        r[2] += t["net"]
    print(f"{title:<20}closed  wins     net $")
    for strat, (n, wins, net) in sorted(
            rows.items(), key=lambda kv: -kv[1][2]):
        print(f"  {strat:<18}{n:>6}{wins:>6}{net:>10.2f}")
    if not rows:
        print("  none yet")


def score(db):
    trades = list(closed_trades(db).values())
    board([t for t in trades if t["feed"] != "fixture"],
          "YOUR TRADES")
    drill = [t for t in trades if t["feed"] == "fixture"]
    if drill:
        board(drill, "PRACTICE FILE")
    cards = db.execute(
        "SELECT payload_json FROM decision_events "
        "WHERE event_type = 'test_card' ORDER BY rowid")
    latest = {}
    for (body,) in cards:
        c = json.loads(body)
        latest[(c["symbol"], c["strategy"])] = c
    if latest:
        print("PAST MARKETS        trades beat?  "
              "net $ per 1,000")
    ranked = sorted(latest.values(), key=lambda c: -c["net_usd"])
    for c in ranked:
        name = f"{c['strategy']} {c['symbol']}"
        print(f"  {name:<18}{c['trades']:>6}{c['beat']:>6}"
              f"{c['net_usd']:>10.2f}")


def last_lock(db):
    return db.execute(
        "SELECT event_id, payload_json, rowid FROM "
        "decision_events WHERE event_type = 'rule_set' "
        "ORDER BY rowid DESC LIMIT 1").fetchone()


def add_cards(db, cards):
    """Past-markets scorecards, filed under the current lock."""
    lock, added = last_lock(db), 0
    for c in cards:
        try:
            record(db, f"T-{c['symbol']}", "test_card", "human",
                   c, lock[0] if lock else None,
                   c["window"][1] + "T21:00:00Z",
                   strategy_version=
                   f"{c['strategy']}@{c['sha256']}")
            db.commit()
            added += 1
        except sqlite3.IntegrityError:
            db.rollback()
    return added


def exec_stats(db, since=0):
    """How the swarm's own orders went, for the ladder."""
    sent, filled, worst = set(), 0, 0.0
    rows = db.execute(
        "SELECT event_type, payload_json FROM decision_events "
        "WHERE event_type IN ('decision', 'submitted', 'fill') "
        "AND source_packet_id IS NOT NULL AND rowid > ? "
        "ORDER BY rowid", (since,))
    for kind, body in rows:
        p = json.loads(body)
        if kind == "decision" and p.get("order"):
            worst = max(worst, p["order"].get(
                "pct_of_daily_volume", 0.0))
        elif kind == "submitted" and p.get("side") == "buy":
            sent.add(p["broker_order_id"])
        elif kind == "fill" and p.get("broker_order_id") in sent:
            filled += 1
    miss = 100 * (len(sent) - filled) / len(sent) if sent else 0
    return {"unfilled_pct": round(miss),
            "order_pct_of_volume": round(worst, 4),
            "broken_rows": len(verify(db))}


def drift(db):
    """Did a rule file change after the swarm traded it?"""
    live = setups.load_all()
    old = setups.load_all("strategies/retired")
    seen = db.execute("SELECT DISTINCT strategy_version FROM "
                      "decision_events WHERE strategy_version "
                      "!= 'none'")
    for (version,) in seen:
        sid, sha = version.split("@")
        if live.get(sid, {}).get("sha256") == sha:
            state = "same file"
        elif old.get(sid, {}).get("sha256") == sha:
            state = "retired, same file"
        else:
            state = ("CHANGED on disk\n"
                     "  save edits as a new version")
        print(f"{sid}: traded as {sha}, {state}")


def tamper(db):
    tests = [
        ("UPDATE", "UPDATE decision_events SET role = 'x'"),
        ("DELETE", "DELETE FROM decision_events"),
        ("REPLACE", "INSERT OR REPLACE INTO decision_events "
         "SELECT * FROM decision_events LIMIT 1"),
    ]
    for name, sql in tests:
        try:
            db.execute(sql)
            print(f"{name:<8} went through. The ledger is open.")
        except sqlite3.Error as err:
            print(f"{name:<8} refused: {err}")
        db.rollback()


if __name__ == "__main__":
    db, cmd = connect(), sys.argv[1]
    if cmd == "add":
        for path in sys.argv[2:]:
            data = json.load(open(path))
            try:
                if "events" in data:
                    n = add_events(db, data["decision_id"],
                                   data["events"])
                elif "cards" in data:
                    n = add_cards(db, data["cards"])
                else:
                    n = add_run(db, data)
                print(f"{path}: {n} rows added")
            except sqlite3.IntegrityError:
                db.rollback()
                print(f"{path}: already in the ledger")
    elif cmd == "trace":
        trace(db, sys.argv[2])
    elif cmd == "score":
        score(db)
    elif cmd == "rules":
        drift(db)
    elif cmd == "tamper":
        tamper(db)
    elif cmd == "verify":
        bad = verify(db)
        total = db.execute(
            "SELECT COUNT(*) FROM decision_events").fetchone()[0]
        print(f"{total} rows, {len(bad)} with a broken hash")
