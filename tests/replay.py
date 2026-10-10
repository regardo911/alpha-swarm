"""replay.py - does this copy of the desk still print the book's output?

It copies the folder to a temporary place, runs the book's practice
drills there in the book's order, and compares every line and exit
code with tests/expected.txt. Your own ledger.db, runs/ and settings
are never touched. No key is read and the network is blocked, so a
drill that reaches for a broker, a data service or a model fails.

    python tests/replay.py             replay and compare
    python tests/replay.py --no-skip   a skipped drill is a failure
    python tests/replay.py --save      keep this run as expected.txt
"""
import difflib
import glob
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DESK = os.path.dirname(HERE)
EXPECTED = os.path.join(HERE, "expected.txt")
INSTALL = "python -m pip install alpaca-py==0.44.0"
HAVE_ALPACA = importlib.util.find_spec("alpaca") is not None

# what the desk writes, and what is yours alone. none of it is copied.
LEAVE = shutil.ignore_patterns(
    ".git", ".github", ".venv", "__pycache__", "docs", "tests",
    "ledger.db", "packets", "runs", "orders", "cards", "bars",
    "sheets", "keys.env", "morning.log", "bad.json", "swarm.real.json")
KEY_NAMES = ("APCA_API_KEY_ID", "APCA_API_SECRET_KEY", "MASSIVE_API_KEY",
             "APCA_LIVE_API_KEY_ID", "APCA_LIVE_API_SECRET_KEY",
             "OPENAI_API_KEY", "ANTHROPIC_API_KEY")
# broker.py reads these two names before it checks the cap, so the two
# refusal drills need some text in them. this text opens nothing.
STAND_INS = {"APCA_API_KEY_ID": "not-a-key",
             "APCA_API_SECRET_KEY": "not-a-secret"}
SCRIPTED = {"provider": "script", "model": "none"}

# every drill starts here. a socket call is written down and refused
# before the book's file gets a line in.
BOOT = '''
import os, runpy, socket, sys

def refuse(what, first):
    def stop(*args, **kwargs):
        with open(os.environ["REPLAY_NET_LOG"], "a") as log:
            log.write(f"{what} {args[first:first + 1]}\\n")
        raise OSError("the replay blocks the network")
    return stop

for name in ("connect", "connect_ex", "sendto"):
    setattr(socket.socket, name, refuse(name, 1))
for name in ("getaddrinfo", "gethostbyname", "create_connection"):
    setattr(socket, name, refuse(name, 0))
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name="__main__")
'''


class Stop(Exception):
    pass


def blocks(path):
    """expected.txt as a list, one '$ command ... [exit n]' per drill."""
    if not os.path.exists(path):
        return []
    text = open(path, encoding="utf-8").read()
    return re.findall(r"^\$ .*?^\[exit -?\d+\]\n", text, re.M | re.S)


def stage(tmp):
    """Copy the desk, then put the copy where the drills start: three
    v1 rules, scripted seats, the mandate and pullback-v2 waiting."""
    at, aside = os.path.join(tmp, "alpha-swarm"), os.path.join(tmp, "aside")
    shutil.copytree(DESK, at, ignore=LEAVE)
    os.mkdir(aside)
    rules = os.path.join(at, "strategies")
    back = glob.glob(os.path.join(rules, "retired", "*.json"))
    for path in back:                   # you finished chapter 11
        shutil.move(path, os.path.join(rules, os.path.basename(path)))
    shutil.rmtree(os.path.join(rules, "retired"), ignore_errors=True)
    if back:
        print(f"note: {len(back)} retired rule(s) put back on the desk, "
              "in the replay's copy only")
    for name, home in (("mandate.json", "05-*"),
                       ("strategies/pullback-v2.json", "11-*")):
        mine = os.path.join(at, name)
        book = glob.glob(os.path.join(
            at, "chapters", home, os.path.basename(name)))
        if not book and not os.path.exists(mine):
            raise Stop(f"{os.path.basename(name)} is not in chapters/ "
                       "and not in this folder")
        if not book:
            print(f"note: using your own {name}")
        shutil.copy(book[0] if book else mine,
                    os.path.join(aside, os.path.basename(name)))
        if os.path.exists(mine):
            os.remove(mine)
    cfg_path = os.path.join(at, "swarm.json")
    cfg = json.load(open(cfg_path))
    real = [s for s in ("research", "thesis", "challenge", "risk")
            if cfg["seats"][s] != SCRIPTED]
    if real:                            # chapter 4, step 7, done for you
        print(f"note: {', '.join(real)} seated with real models; the "
              "replay's copy uses the scripted seats")
        for seat in real:
            cfg["seats"][seat] = dict(SCRIPTED)
    cfg["scene"] = "first"
    with open(cfg_path, "w") as f:
        json.dump(cfg, f, indent=2)
    return at, aside


class Replay:
    def __init__(self, at, aside, env, log, expected):
        self.at, self.aside, self.env, self.log = at, aside, env, log
        self.expected, self.got = expected, []      # [] when saving
        self.differ, self.skipped, self.net = [], [], 0

    def path(self, name):
        return os.path.join(self.at, *name.split("/"))

    def run(self, *args, alpaca=False):
        """One drill. alpaca=True: it needs alpaca-py to match."""
        label = "python " + " ".join(args)
        if alpaca and not HAVE_ALPACA:
            self.skipped.append(label)
            self.got.append(None)
            print(f"{len(self.got):>3}  skip  {label}")
            return ""
        env = dict(self.env, **STAND_INS) if alpaca else self.env
        done = subprocess.run(
            [sys.executable, "-c", BOOT, *args], cwd=self.at, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.keep(label, done.stdout, done.returncode)
        return done.stdout

    def keep(self, label, out, code):
        if out and not out.endswith("\n"):
            out += "\n"
        block = f"$ {label}\n{out}[exit {code}]\n"
        self.got.append(block)
        n = len(self.got)
        tried = open(self.log).read().splitlines()[self.net:]
        self.net += len(tried)
        want = self.expected[n - 1] if n <= len(self.expected) else ""
        if tried:
            self.differ.append(n)
            print(f"{n:>3}  NET   {label}")
            print(f"       tried to open a connection: {tried[0]}")
        elif not self.expected:
            print(f"{n:>3}  ran   {label}")
        elif block != want:
            self.differ.append(n)
            print(f"{n:>3}  DIFF  {label}")
            for line in list(difflib.unified_diff(
                    want.splitlines(), block.splitlines(),
                    "expected", "this copy", lineterm=""))[:24]:
                print(f"       {line}")
        else:
            print(f"{n:>3}  ok    {label}")

    def edit(self, name, old, new, to=None):
        """One of the edits the book has you make by hand. Returns the
        file as it was, so it can be put back."""
        before = open(self.path(name), "rb").read()
        if before.count(old.encode()) != 1:
            # your copy already differs here. say so and carry on: the
            # drills that follow will show what that changes
            print(f"note: {name} has no {old}, so the book's edit to "
                  "it was not made")
            return None
        self.put(to or name, before.replace(old.encode(), new.encode()))
        return before

    def put(self, name, data):
        if data is not None:
            with open(self.path(name), "wb") as f:
                f.write(data)

    def scene(self, name):
        cfg = json.load(open(self.path("swarm.json")))
        cfg["scene"] = name
        self.put("swarm.json", json.dumps(cfg, indent=2).encode())

    def take(self, name):
        shutil.copy(os.path.join(self.aside, os.path.basename(name)),
                    self.path(name))

    def lock(self):
        # two locks inside one second are one lock, and the second half
        # of chapter 11 then files its cards under the first
        time.sleep(1.2)
        self.run("retire.py", "lock")

    def ls(self, *folders):
        # the book's ls, done here so the replay needs no shell
        out = "\n\n".join(
            f"{f}:\n" + "\n".join(sorted(os.listdir(self.path(f))))
            for f in folders)
        self.keep("ls " + " ".join(folders), out, 0)


def saved(out, folder):
    """The file a drill said it saved. Later drills are pointed at it."""
    m = re.search(rf"^saved ({folder}/\S+)$", out, re.M)
    return m.group(1) if m else f"{folder}/nothing-was-saved.json"


def drills(r):
    # chapter 2
    r.run("check_charter.py")
    r.edit("charter.json", '"owns": "what to buy and at what limit"',
           '"owns": "how many dollars go on the trade"', to="bad.json")
    r.run("check_charter.py", "bad.json")
    r.edit("charter.json", '"input": "thesis", "output": "verdict"',
           '"input": "brief", "output": "verdict"', to="bad.json")
    r.run("check_charter.py", "bad.json")
    if os.path.exists(r.path("bad.json")):
        os.remove(r.path("bad.json"))
    # chapter 3
    r.run("make_fixture.py")
    packet = saved(r.run("packet.py", "DEMO", "--fixture"), "packets")
    r.run("packet.py", "scan", "--fixture")
    # chapter 4
    run = saved(r.run("swarm.py", packet), "runs")
    decision = os.path.basename(run)[:-len(".json")]
    r.scene("broken")
    r.run("swarm.py", packet)
    r.scene("first")
    # chapter 5: both sends are refused on this machine
    r.take("mandate.json")
    signed = r.edit("mandate.json", '"cap_usd": 100', '"cap_usd": 50')
    r.run("broker.py", "send", run, alpaca=True)
    r.put("mandate.json", signed)
    r.run("broker.py", "send", run, alpaca=True)
    # chapter 6
    r.scene("rework")
    r.run("swarm.py", packet)
    r.scene("greedy")
    r.run("swarm.py", packet)
    r.scene("first")
    r.run("swarm.py", packet, "price=73.10")
    r.run("swarm.py", packet, "now=2023-11-29T14:30:00Z")
    r.run("swarm.py", packet, "open=3")
    r.run("swarm.py", packet)
    # chapter 7
    r.run("ledger.py", "add", run)
    r.run("ledger.py", "add", run)
    r.run("ledger.py", "trace", decision)
    r.run("ledger.py", "add", "fixtures/events_DEMO.json")
    r.run("ledger.py", "trace", decision)
    r.run("ledger.py", "tamper")
    r.run("ledger.py", "verify")
    r.run("ledger.py", "rules")
    rule = r.edit("strategies/breakout-v1.json",
                  '"stop_pct": 0.06', '"stop_pct": 0.05')
    r.run("ledger.py", "rules")
    r.put("strategies/breakout-v1.json", rule)
    r.run("ledger.py", "rules")
    r.run("ledger.py", "score")
    # chapter 8
    r.run("walkforward.py", "DEMO")
    r.run("walkforward.py", "DEMO", "breakout-v1")
    r.run("walkforward.py", "DEMO", "bounce-v1")
    r.run("ledger.py", "add", "cards/DEMO.json")
    r.run("ledger.py", "score")
    # chapter 9
    r.run("costs.py", run, "--record")
    r.run("ledger.py", "trace", decision)
    r.run("costs.py", "lineups", "fixtures/tokens_DEMO.json")
    r.run("ledger.py", "score")
    # chapter 10
    r.run("ladder.py")
    r.run("ladder.py", "fixtures/record_DEMO.json")
    signed = r.edit("mandate.json", '"mode": "practice"', '"mode": "live"')
    r.run("ladder.py")
    r.put("mandate.json", signed)
    # chapter 11
    r.run("retire.py")
    r.lock()
    r.run("walkforward.py", "DEMO")
    r.run("ledger.py", "add", "cards/DEMO.json")
    r.run("retire.py")
    locked = r.edit("stop_rules.json", '"retire_if_net_usd_below": 0',
                    '"retire_if_net_usd_below": -100')
    r.run("retire.py")
    r.put("stop_rules.json", locked)
    r.run("retire.py")
    os.mkdir(r.path("strategies/retired"))
    for name in ("bounce-v1.json", "pullback-v1.json"):
        if os.path.exists(r.path(f"strategies/{name}")):
            shutil.move(r.path(f"strategies/{name}"),
                        r.path(f"strategies/retired/{name}"))
    r.take("strategies/pullback-v2.json")
    r.ls("strategies", "strategies/retired")
    r.run("packet.py", "scan", "--fixture")
    r.lock()
    r.run("walkforward.py", "DEMO")
    r.run("ledger.py", "add", "cards/DEMO.json")
    r.run("retire.py")
    r.run("ledger.py", "rules")
    # chapter 12. daily.py imports broker.py, so week needs alpaca-py.
    # week also signs the practice mandate into the ledger once more,
    # and the last row count only holds if it ran.
    r.run("daily.py", "week", alpaca=True)
    r.run("ledger.py", "verify", alpaca=True)


def pages(expected):
    """A ```text block on a page is practice output, so it has to be
    in expected.txt. Shapes with <brackets> use a bare fence."""
    outputs = [[line.rstrip() for line in b.splitlines()[1:-1]]
               for b in expected]
    found, missing = 0, []
    names = [os.path.join(DESK, "README.md")] + sorted(glob.glob(
        os.path.join(DESK, "chapters", "*", "README.md")))
    for name in names:
        if not os.path.exists(name):
            continue
        text = open(name, encoding="utf-8").read()
        for pad, body in re.findall(r"^( *)```text\n(.*?)^\1```$",
                                    text, re.M | re.S):
            want = [line[len(pad):].rstrip() for line in body.splitlines()]
            if any(want == out[i:i + len(want)] for out in outputs
                   for i in range(len(out) - len(want) + 1)):
                found += 1
            else:
                missing.append((os.path.relpath(name, DESK), want[0]))
    print(f"pages: {found + len(missing)} output blocks, "
          f"{found} found in expected.txt")
    for name, first in missing:
        print(f"  {name}: no drill prints the block starting '{first}'")
    return not missing


def main(argv):
    save, strict = "--save" in argv, "--no-skip" in argv
    expected = [] if save else blocks(EXPECTED)
    if not save and not expected:
        print("tests/expected.txt is missing or empty: nothing to "
              "compare with")
        return 1
    if sys.version_info < (3, 12):      # see BOOK-FIXES.md
        print(f"note: this is Python {sys.version.split()[0]}. The "
              "book's packet and decision numbers need 3.12 or newer")
    with tempfile.TemporaryDirectory() as tmp:
        log = os.path.join(tmp, "net.log")
        open(log, "w").close()
        env = {k: v for k, v in os.environ.items() if k not in KEY_NAMES}
        env.update(REPLAY_NET_LOG=log, PYTHONUNBUFFERED="1")
        try:
            r = Replay(*stage(tmp), env, log, expected)
        except Stop as why:
            print(f"stopped before the first drill: {why}")
            return 1
        drills(r)
    ran = [b for b in r.got if b]
    if save:
        if r.skipped or r.net:
            print("not saved: no drill may be skipped and no "
                  "connection opened")
            return 1
        with open(EXPECTED, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(ran))
        print(f"saved tests/expected.txt ({len(ran)} drills)")
        return 0 if pages(blocks(EXPECTED)) else 1
    ok = pages(expected)
    print(f"network: blocked for every drill, {r.net} connection(s) tried")
    total = max(len(r.got), len(r.expected))
    line = f"{total} drills, {len(ran) - len(r.differ)} match"
    if r.differ:
        line += f", {len(r.differ)} differ: " + ", ".join(map(str, r.differ))
    if r.skipped:
        line += (f", {len(r.skipped)} skipped (they need alpaca-py: "
                 f"{INSTALL})")
    print(line)
    bad = (r.differ or not ran or not ok or len(r.got) != total
           or (strict and r.skipped))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
