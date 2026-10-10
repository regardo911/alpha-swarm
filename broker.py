"""broker.py - the execution seat's line to the broker.

It sends exactly the order the desk approved, reads the
broker's answer back, and checks the two match. It cannot
change a symbol, a side, a size or a limit.
"""
import json
import os
import sys
from datetime import datetime, timezone

from alpaca.common.exceptions import APIError
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import LimitOrderRequest

import keys

WAITING = ("accepted", "pending_new", "new", "partially_filled")


def now():
    return datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def connect():
    """Practice unless the signed mandate says live."""
    keys.load()
    mandate = json.load(open("mandate.json"))
    live = mandate["mode"] == "live"
    tag = "APCA_LIVE" if live else "APCA"
    client = TradingClient(os.environ[tag + "_API_KEY_ID"],
                           os.environ[tag + "_API_SECRET_KEY"],
                           paper=not live)
    return client, mandate


def find(client, cid):
    try:
        return client.get_order_by_client_id(cid)
    except APIError:
        return None


def snapshot(order, event):
    """The broker's answer, flattened for the ledger. A fill
    carries the broker's own time, not the time this machine
    asked."""
    done = getattr(order, "filled_at", None)
    happened = (done.astimezone(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ") if done else now())
    return {"event": event, "broker_order_id": str(order.id),
            "status": order.status.value,
            "symbol": order.symbol, "side": order.side.value,
            "qty": float(order.qty),
            "limit_price": float(order.limit_price),
            "filled_qty": float(order.filled_qty or 0),
            "filled_avg_price": float(
                order.filled_avg_price or 0),
            "event_time_utc": happened,
            "observed_at_utc": now()}


def save(record):
    os.makedirs("orders", exist_ok=True)
    path = f"orders/{record['decision_id']}.json"
    with open(path, "w") as f:
        json.dump(record, f, indent=1)
    return path


def send(run, side="buy", qty=None, limit=None, tag=""):
    """Send one approved order. Safe to run twice."""
    want = dict(run["order"], side=side)
    want["qty"] = qty or want["qty"]
    want["limit_price"] = round(limit or want["limit_price"], 2)
    client, mandate = connect()
    cost = want["qty"] * want["limit_price"]
    if side == "buy" and cost > mandate["cap_usd"]:
        cap = mandate["cap_usd"]
        raise SystemExit(f"REFUSED here: ${cost:.2f} is over "
                         f"the signed cap of ${cap}")
    if run.get("feed") == "fixture":
        raise SystemExit("REFUSED here: a practice-file "
                         "decision, not a real stock")
    cid = f"swarm-{run['decision_id']}{tag}"
    path = f"orders/{run['decision_id']}.json"
    record = (json.load(open(path)) if os.path.exists(path) else
              {"decision_id": run["decision_id"], "events": []})
    order = find(client, cid)
    if order is None:
        try:
            order = client.submit_order(LimitOrderRequest(
                symbol=want["symbol"], qty=want["qty"],
                side=OrderSide(side), limit_price=want[
                    "limit_price"], client_order_id=cid,
                time_in_force=TimeInForce.DAY))
        except (APIError, ValueError) as err:
            try:                # the broker's own words
                why = str(err.message)
            except Exception:   # no message, or not JSON
                why = str(err)
            record["events"].append({
                "event": "refused", "side": side,
                "message": why,
                "event_time_utc": now(),
                "observed_at_utc": now()})
            print("broker refused: "
                  + record["events"][-1]["message"])
            return save(record), None
    else:
        print("already at the broker, not sent again")
    got = snapshot(order, "submitted")
    got["client_order_id"] = cid
    seen = {e.get("client_order_id") for e in record["events"]}
    if cid not in seen:
        record["events"].append(got)
    match = all(got[k] == want[k] for k in
                ("symbol", "side", "qty", "limit_price"))
    print(f"order id   {got['broker_order_id']}")
    print(f"status     {got['status']}, "
          f"filled {got['filled_qty']:g}")
    print(f"sent       {want['side']} {want['qty']:g} "
          f"{want['symbol']} limit {want['limit_price']:.2f}")
    print(f"broker has {got['side']} {got['qty']:g} "
          f"{got['symbol']} limit {got['limit_price']:.2f}")
    print("MATCH" if match else "MISMATCH: stop and look")
    return save(record), got


def check(decision_id):
    """Ask the broker where each of this decision's orders is."""
    client, _ = connect()
    path = f"orders/{decision_id}.json"
    record = json.load(open(path))
    sent = [e for e in record["events"]
            if e["event"] == "submitted"]
    for first in sent:
        order = find(client, first["client_order_id"])
        if order is None:
            continue
        got = snapshot(order, order.status.value)
        mine = [e for e in record["events"]
                if e["event"] in ("fill", "partial_fill")
                and e["broker_order_id"] == got[
                    "broker_order_id"]]
        done = sum(e["qty"] for e in mine)
        paid = sum(e["qty"] * e["price"] for e in mine)
        fresh = got["filled_qty"] - done
        if fresh > 0:
            kind = ("fill" if got["status"] == "filled"
                    else "partial_fill")
            total = got["filled_qty"] * got["filled_avg_price"]
            record["events"].append(dict(
                got, event=kind, qty=fresh,
                price=round((total - paid) / fresh, 4)))
        elif got["status"] not in WAITING + ("filled",):
            if not any(e["event"] == got["status"]
                       for e in record["events"]):
                record["events"].append(got)
        print(f"{first['client_order_id']}: {got['status']}, "
              f"filled {got['filled_qty']:g} of {got['qty']:g}")
    return save(record)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "clock":
        c = connect()[0].get_clock()
        print(f"market open now: {c.is_open}")
        print(f"next open:  {c.next_open}")
        print(f"next close: {c.next_close}")
    elif cmd == "account":
        a = connect()[0].get_account()
        print(f"status {a.status.value}, cash ${a.cash}, "
              f"buying power ${a.buying_power}")
    elif cmd == "send":
        run = json.load(open(sys.argv[2]))
        if run["status"] != "RISK_APPROVED":
            raise SystemExit(f"nothing to send: {run['status']}")
        print(f"saved {send(run)[0]}")
    elif cmd == "check":
        print(f"saved {check(sys.argv[2])}")
    elif cmd == "cancel":
        client, _ = connect()
        order = find(client, f"swarm-{sys.argv[2]}")
        client.cancel_order_by_id(order.id)
        print(f"cancel sent for {order.id}")
    elif cmd in ("test", "slice"):
        # a drill order 10% under the last close: it should wait
        # test = one share, slice = a dollar amount of one share
        p = json.load(open(sys.argv[2]))
        limit = round(p["last_close"] * 0.9, 2)
        qty = (1 if cmd == "test"
               else round(float(sys.argv[3]) / limit, 4))
        drill = {"decision_id": f"{cmd.upper()}-"
                                + p["packet_id"][2:],
                 "order": {"symbol": p["symbol"], "qty": qty,
                           "limit_price": limit}}
        print(f"saved {send(drill)[0]}")
