"""swarm.py - run one trade idea through all five seats.

research > thesis > challenge > risk > execution.
Everything each seat said is saved in runs/<decision id>.json.
"""
import hashlib
import json
import os
import sys

import models
import setups

try:
    import gate                  # arrives in Chapter 6
except ImportError:
    gate = None


def cited(items, packet, seat, strict=True):
    """Keep only claims that cite facts in the packet."""
    known = {f["id"] for f in packet["facts"]}
    kept = []
    for item in items:
        cites = item.get("cites", [])
        if cites and all(c in known for c in cites):
            kept.append(item)
        elif strict:
            raise models.SeatError(
                f"{seat}: unsupported claim, cites {cites}")
    return kept


def check_thesis(run, packet):
    t, rules = run["thesis"], setups.load_all()
    cited(t["reasons"], packet, "thesis")
    rule = rules.get(t["setup"])
    if not rule or t["setup"] not in packet["setups_fired"]:
        raise models.SeatError("thesis: setup did not fire")
    top = setups.entry_limit(rule, packet["last_close"])
    if not 0 < t["limit"] <= top:
        raise models.SeatError(f"thesis: limit above {top:.2f}")
    t["limit"] = round(t["limit"], 2)
    run["setup"] = {"id": rule["id"], "sha256": rule["sha256"]}


def check_challenge(run, packet):
    c = run["challenge"]
    kept = cited(c["objections"], packet, "challenge", False)
    c["dropped"] = len(c["objections"]) - len(kept)
    c["objections"] = kept
    if c["verdict"] not in ("PASS", "REVISE", "REJECT"):
        raise models.SeatError("challenge: unknown verdict")
    if c["verdict"] != "PASS" and not kept:
        raise models.SeatError("challenge: verdict with no "
                               "cited objection")


def simple_decide(run, cfg):
    if run["challenge"]["verdict"] == "REJECT":
        return 0, "REJECTED"
    cap = cfg["limits"]["max_position_usd"]
    dollars = min(run["risk"]["dollars"], cap)
    qty = int(dollars // run["thesis"]["limit"])
    return qty, "RISK_APPROVED" if qty else "TOO_SMALL"


def run_desk(run, packet, cfg, charter):
    def seat(name, payload):
        reply, usage = models.ask(name, payload, cfg, charter)
        run["usage"].setdefault(name, []).append(usage)
        run["log"].append(name)
        return reply

    run["brief"] = seat("research", {"packet": packet})
    cited(run["brief"]["observations"], packet, "research")
    fired = packet["setups_fired"]
    if not run["brief"]["worth_a_thesis"] or not fired:
        run["status"] = "NO_IDEA"
        return
    run["thesis"] = seat("thesis", {
        "packet": packet, "brief": run["brief"],
        "allowed_setups": fired})
    check_thesis(run, packet)
    run["challenge"] = seat("challenge", {
        "packet": packet, "thesis": run["thesis"]})
    check_challenge(run, packet)
    if gate:
        gate.rework(run, packet, seat,
                    check_thesis, check_challenge)
        if run["challenge"]["verdict"] != "PASS":
            run["status"] = "REJECTED"
            return
    rule = setups.load_all()[run["setup"]["id"]]
    run["risk"] = seat("risk", {
        "thesis": run["thesis"], "challenge": run["challenge"],
        "account_usd": cfg["account_usd"],
        "open_positions": run["open_positions"],
        "limits": cfg["limits"], "exit_rules": rule["exit"]})
    decide = gate.decide if gate else simple_decide
    qty, run["status"] = decide(run, cfg)
    if run["status"] == "RISK_APPROVED":
        run["order"] = {
            "symbol": packet["symbol"], "side": "buy",
            "qty": qty, "limit_price": run["thesis"]["limit"],
            "time_in_force": "day",
            "client_order_id": "swarm-" + run["decision_id"],
            "pct_of_daily_volume": round(
                100 * qty * run["thesis"]["limit"]
                / packet["avg_usd_volume"], 4)}
        run["log"].append("execution")


def main(path, now=None, price=None, open_positions=0):
    packet = json.load(open(path))
    cfg = json.load(open("swarm.json"))
    charter = json.load(open("charter.json"))
    seed = packet["packet_id"] + cfg.get("scene", "")
    did = "D-" + hashlib.sha256(seed.encode()).hexdigest()[:8]
    practice = packet["market"][0]["feed"] == "fixture"
    run = {"decision_id": did, "packet_id": packet["packet_id"],
           "symbol": packet["symbol"], "usage": {}, "log": [],
           "as_of_utc": packet["as_of_utc"],
           "feed": packet["market"][0]["feed"],
           "clock_utc": now or (packet["created_at_utc"]
                                if practice else None),
           "last_price": price or packet["last_close"],
           "open_positions": open_positions}
    try:
        run_desk(run, packet, cfg, charter)
    except Exception as err:    # any break at all: no order
        run["status"], run["error"] = "NO_ORDER", str(err)
    os.makedirs("runs", exist_ok=True)
    with open(f"runs/{did}.json", "w") as f:
        json.dump(run, f, indent=1)
    return run


def show(run):
    print(f"decision {run['decision_id']}  {run['symbol']}")
    if "thesis" in run:
        t = run["thesis"]
        lim = t["limit"]
        if isinstance(lim, (int, float)):
            lim = f"{lim:.2f}"  # a broken reply prints as sent
        print(f"  thesis     buy at {lim} "
              f"on {t['setup']}")
    if "challenge" in run:
        c = run["challenge"]
        again = ", after 1 rework" if run.get("rounds") else ""
        count = len(c["objections"] or [])
        print(f"  challenge  {c['verdict']}, "
              f"{count} objection(s){again}")
    if "risk" in run:
        r = run["risk"]
        print(f"  risk       {r['vote']} ${r['dollars']}")
    if "order" in run:
        o = run["order"]
        print(f"  order      {o['side']} {o['qty']} "
              f"{o['symbol']} limit {o['limit_price']:.2f} "
              f"{o['time_in_force']}")
    print(f"  status     {run['status']}")
    for key in ("error", "why"):
        if key in run:
            print(f"  {key:<10} {run[key]}")
    print(f"saved runs/{run['decision_id']}.json")


if __name__ == "__main__":
    args = dict(a.split("=") for a in sys.argv[2:])
    show(main(sys.argv[1], now=args.get("now"),
              price=float(args["price"]) if "price" in args
              else None,
              open_positions=int(args.get("open", 0))))
