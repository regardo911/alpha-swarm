"""gate.py - the argument, the clock and the hard limits.

swarm.py uses this file as soon as it exists. Nothing here
asks a model for permission. Code decides every refusal.
"""
from datetime import datetime, timezone


def when(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def rework(run, packet, seat, check_thesis, check_challenge):
    """A REVISE sends the objections back to thesis, once."""
    if run["challenge"]["verdict"] != "REVISE":
        return
    run["rounds"] = 1
    run["first_thesis"] = run["thesis"]
    run["first_challenge"] = run["challenge"]
    run["thesis"] = seat("thesis", {
        "packet": packet, "brief": run["brief"],
        "allowed_setups": [run["first_thesis"]["setup"]],
        "your_last_thesis": run["first_thesis"],
        "objections": run["challenge"]["objections"]})
    check_thesis(run, packet)
    run["challenge"] = seat("challenge", {
        "packet": packet, "thesis": run["thesis"],
        "first_thesis": run["first_thesis"]})
    check_challenge(run, packet)
    if run["challenge"]["verdict"] == "REVISE":
        run["challenge"]["verdict"] = "REJECT"
        run["why"] = "still disputed after one rework"


def decide(run, cfg):
    """Return (qty, status). Code only."""
    lim, t, r = cfg["limits"], run["thesis"], run["risk"]
    now = (when(run["clock_utc"]) if run.get("clock_utc")
           else datetime.now(timezone.utc))
    if now >= when(t["expires_utc"]):
        run["why"] = f"thesis died {t['expires_utc']}"
        return 0, "EXPIRED"
    top = t["limit"] * (1 + lim["max_chase_pct"])
    if run["last_price"] > top:
        run["why"] = (f"price {run['last_price']:.2f} is past "
                      f"{top:.2f}, the most this desk chases")
        return 0, "EXPIRED"
    if (r["vote"] not in ("APPROVE", "REDUCE")
            or r["dollars"] <= 0):
        run["why"] = "risk seat veto"
        return 0, "VETOED"
    if run["open_positions"] >= lim["max_open_positions"]:
        run["why"] = (f"{run['open_positions']} positions open, "
                      f"hard limit {lim['max_open_positions']}")
        return 0, "VETOED"
    dollars = min(r["dollars"], lim["max_position_usd"])
    if dollars < r["dollars"]:
        run["why"] = (f"risk asked ${r['dollars']}, "
                      f"hard limit gave ${dollars}")
    qty = int(dollars // t["limit"])
    if not qty:
        run["why"] = (f"${dollars} buys less than one share "
                      f"at {t['limit']:.2f}")
    return qty, "RISK_APPROVED" if qty else "TOO_SMALL"
