"""check_charter.py - one job per agent, no overlaps."""
import json
import sys

ORDER = ["research", "thesis", "challenge", "risk", "execution"]


def check(path="charter.json"):
    charter = json.load(open(path))
    roles, problems = charter["roles"], []
    ids = [r["id"] for r in roles]
    if ids != ORDER:
        problems.append(f"ROLES: expected {ORDER}, got {ids}")
    for r in roles:
        for field in ("input", "output", "owns", "keys",
                      "may_not"):
            if not r.get(field):
                problems.append(f"EMPTY: {r['id']}.{field}")
    chain = ["packet"]
    for r in roles:
        if r.get("input") != chain[-1]:
            problems.append(f"CHAIN: {r['id']} reads "
                            f"'{r.get('input')}'\n  the seat "
                            f"before it writes '{chain[-1]}'")
        chain.append(r.get("output"))
    owners = {}
    for r in roles:
        owners.setdefault(r.get("owns"), []).append(r["id"])
    for job, who in owners.items():
        if len(who) > 1:
            problems.append(f"OVERLAP: {' and '.join(who)} "
                            f"both own\n  '{job}'")
    if len(charter.get("human", [])) < 3:
        problems.append("HUMAN: list the three calls you keep")
    if problems:
        print("\n".join(problems))
        print(f"CHARTER BROKEN: {len(problems)} problem(s)")
        return False
    print(f"{len(roles)} roles: {' > '.join(ids)}")
    print(f"chain OK: {' > '.join(chain)}")
    print(f"{len(owners)} decisions, 0 overlaps")
    print("the human keeps:")
    for call in charter["human"]:
        print(f"  {call}")
    print("CHARTER OK")
    return True


if __name__ == "__main__":
    sys.exit(0 if check(*sys.argv[1:]) else 1)
