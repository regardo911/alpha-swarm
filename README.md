# alpha-swarm

**Five AI agents pick a trade on a stock you watch, size it and send it to your broker. By Monday's open the desk runs on a schedule.**

The companion code to the book *AI Trading Agent Alpha Swarm*, from [youcanbuildthings.com](https://youcanbuildthings.com).

[![replay](https://github.com/regardo911/alpha-swarm/actions/workflows/ci.yml/badge.svg)](https://github.com/regardo911/alpha-swarm/actions/workflows/ci.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-111111.svg)](LICENSE)
[![not financial advice](https://img.shields.io/badge/not-financial%20advice-E4572E.svg)](DISCLAIMER.md)

Educational software. Orders go to your broker's practice account until you sign for live money yourself.

![Poster. Wake up to the trade already placed. A dark panel, Waiting for you by Monday's open, holds three screens from the book's practice run on the made-up stock DEMO: the five-agent trade call, the order read back from the broker, and the scorecard. Below, the five agents (Research, Thesis, Challenge, Risk, Execution) and what each one hands you.](docs/images/hero.png)

This is the folder the book has you build, already filled in. You give it a stock symbol. One program gathers that stock's prices and headlines into a numbered list of facts. Four AI models take turns on the list: one says which facts matter, one proposes a trade, one argues against it, one decides how many dollars go on it. Plain code sends the order that survives to your broker and checks the broker got it right. Two words you'll meet straight away: a *packet* is that list of facts ([Chapter 3](chapters/03-build-the-research-desk)), and a *seat* is one of the five jobs ([Chapter 2](chapters/02-give-every-agent-one-job)). Now pick your line.

## Start here

### I want to see five agents make a trade call

No keys, no install, about a minute. You need Python 3.12 or newer, so check `python3 --version` first. No git? Use **Code > Download ZIP** on this page, unzip it, rename the folder to `alpha-swarm`, and start at the `cd` line.

```bash
git clone https://github.com/regardo911/alpha-swarm.git
cd alpha-swarm
python3 -m venv .venv
source .venv/bin/activate
python make_fixture.py
python packet.py DEMO --fixture
python swarm.py packets/P-0390dac823.json
```

On Windows the `source` line is different, and Python's own `venv` page has the one for your shell. The last command prints the trade call:

```text
decision D-f01824fc  DEMO
  thesis     buy at 70.96 on breakout-v1
  challenge  PASS, 2 objection(s)
  risk       REDUCE $80
  order      buy 1 DEMO limit 70.96 day
  status     RISK_APPROVED
saved runs/D-f01824fc.json
```

You just built a practice stock, froze its facts into `packets/`, and sent one idea past all five seats. `runs/D-f01824fc.json` holds what each seat said. DEMO is a made-up stock whose prices come from a formula, which is why your screen matches this page digit for digit.

### I have my keys and want a call on my own stock

Same folder, on your accounts: a free Alpaca practice account, a free Massive key and one model key.

```bash
python -m pip install alpaca-py==0.44.0
cp keys.env.example keys.env
```

1. Put your keys in `keys.env` and your own symbols in the `watchlist` line of `swarm.json`. `python packet.py scan` shows which of them fired a setup today, and `python packet.py XYZ` builds the packet for one that did. ([Chapter 3](chapters/03-build-the-research-desk))
2. Seat real models in `swarm.json` and run `python swarm.py packets/P-<yours>.json`. ([Chapter 4](chapters/04-run-the-first-trade))
3. Copy `chapters/05-connect-to-your-broker/mandate.json` into the folder, put your name and the date in it, and run `python broker.py send runs/D-<yours>.json`. It ends with an order id from your broker and the word `MATCH`. ([Chapter 5](chapters/05-connect-to-your-broker))

### I'm partway through the book and want one file

Go to [the table below](#every-chapter-every-file). Every file sits at the path the book gives it, apart from the two the table marks.

### The weekend is done

[Chapter 12](chapters/12-schedule-the-morning-run) puts the desk on a schedule. After that your job is one command a week: `python daily.py week`.

## Every chapter, every file

Each chapter name opens that chapter's page: commands, output, and how to aim them at your own stock.

| Chapter | Files it adds | Run | You'll see | Your keys |
|---|---|---|---|---|
| [2. Give every agent one job](chapters/02-give-every-agent-one-job) | [`charter.json`](charter.json), [`roles/`](roles), [`check_charter.py`](check_charter.py), [`swarm.json`](swarm.json) | `python check_charter.py` | `CHARTER OK` | none |
| [3. Build the research desk](chapters/03-build-the-research-desk) | [`make_fixture.py`](make_fixture.py), [`strategies/`](strategies), [`setups.py`](setups.py), [`packet.py`](packet.py), [`keys.py`](keys.py), [`live.py`](live.py) | `python packet.py DEMO --fixture` | `11 facts, 6 sources, 1 flag(s)` | Alpaca and Massive, for your own stock |
| [4. Run the first trade](chapters/04-run-the-first-trade) | [`models.py`](models.py), [`swarm.py`](swarm.py), [`fixtures/seats/`](fixtures/seats) | `python swarm.py packets/P-0390dac823.json` | `status     RISK_APPROVED` | a model key, for real seats |
| [5. Connect to your broker](chapters/05-connect-to-your-broker) | [`broker.py`](broker.py), [`mandate.json`](chapters/05-connect-to-your-broker/mandate.json) (copy it to the root and sign it) | `python broker.py send runs/D-<yours>.json` | `MATCH` | Alpaca practice |
| [6. Make agents disagree](chapters/06-make-agents-disagree) | [`gate.py`](gate.py), two more scenes in [`fixtures/seats/`](fixtures/seats) | `python swarm.py packets/P-0390dac823.json price=73.10` | `status     EXPIRED` | none |
| [7. Record every decision](chapters/07-record-every-decision) | [`ledger.py`](ledger.py), [`fixtures/events_DEMO.json`](fixtures/events_DEMO.json) | `python ledger.py tamper` | three lines that say `refused` | none |
| [8. Test on past markets](chapters/08-test-on-past-markets) | [`walkforward.py`](walkforward.py) | `python walkforward.py DEMO` | a `beat?` column | Alpaca, for your own stock |
| [9. Price every decision](chapters/09-price-every-decision) | [`costs.py`](costs.py), [`fixtures/tokens_DEMO.json`](fixtures/tokens_DEMO.json), three new blocks in `swarm.json` | `python costs.py runs/D-f01824fc.json --record` | `break-even move` | none |
| [10. Climb the money ladder](chapters/10-climb-the-money-ladder) | [`ladder.json`](ladder.json), [`ladder.py`](ladder.py), [`fixtures/record_DEMO.json`](fixtures/record_DEMO.json) | `python ladder.py` | `STAY` or `EARNED` | none |
| [11. Retire what loses](chapters/11-retire-what-loses) | [`stop_rules.json`](stop_rules.json), [`retire.py`](retire.py), [`pullback-v2.json`](chapters/11-retire-what-loses/pullback-v2.json) (copy it into `strategies/` at step 6) | `python retire.py` | `CONTINUE`, `REVISE` or `RETIRE` | none |
| [12. Schedule the morning run](chapters/12-schedule-the-morning-run) | [`daily.py`](daily.py), [`com.alphaswarm.morning.plist`](com.alphaswarm.morning.plist), [`morning.sh`](morning.sh) | `python daily.py morning` | a dated file in `sheets/` | all three |

## After the weekend

![Poster. It trades before the open. Three calls stay yours. On the left, the six things the morning run does on its own. On the right, your three calls beside the file each one is: mandate.json, swarm.json, strategies/. Under them, the python daily.py week printout from the book's practice run on the made-up stock DEMO.](docs/images/who-owns-what.png)

One scheduled command works your watchlist every morning: four model seats argue over each idea and code holds every rule. Three calls stay with you, and each one is a file you edit: `mandate.json`, `swarm.json` and the rule files in `strategies/`. `python daily.py week` tells you when one is due.

## What it needs to run

Python 3.12 or newer. The book was written on 3.14.7. The drills replay clean on 3.12, 3.13 and 3.14, and the badge at the top reruns them on Ubuntu and macOS at every push.

One pinned package, `alpaca-py==0.44.0`, for anything that goes through `broker.py`, `live.py` or `daily.py`. Add `openai` or `anthropic` for real model seats, your choice. The rest is Python alone.

Your own accounts get you three things: today's facts and six years of prices for your stocks (`packet.py`, `live.py`), a thesis and a challenge from real models (`swarm.py`), and an order id from your own broker with a sheet each morning (`broker.py`, `daily.py`).

The practice stock, the scripted seats, the ledger and the past-markets test all work with no account, so you can run the desk end to end before you open one.

## Going live

The book's ladder starts on the practice account, then goes to live money at $100, $250, $500 and $1,000 a trade. Each rung is earned by 20 closed trades at the rung below plus five other gates, and `python ladder.py` reads all of them off your own ledger.

You turn live trading on with two edits. Change `"mode": "practice"` to `"mode": "live"` in the `mandate.json` you signed, and add a second pair of Alpaca keys to `keys.env` under the names `APCA_LIVE_API_KEY_ID` and `APCA_LIVE_API_SECRET_KEY`. That is the only switch.

Don't sign for live money until `python ladder.py` says `EARNED` on your own record.

## Check your copy

```bash
python tests/replay.py
```

It replays the book's 55 practice drills in a temporary copy of the folder, with no keys and the network blocked, and compares every line with `tests/expected.txt`. A clean run ends `55 drills, 55 match`. With `alpaca-py` missing it runs 51 and names the 4 it skipped. A mismatch prints the drill and the lines that differ, which is how you see what your edit to a rule or a limit changed.

## Fixes and changes

The 44 book files here are identical to the printed book, so a copy you typed and this folder always agree. If you find a problem in the book's code, open an issue, because a pull request against those files would break that match. [BOOK-FIXES.md](BOOK-FIXES.md) covers the one known mismatch between the printed page and your machine: the Python version.

## License

MIT. See [LICENSE](LICENSE).

Educational software, not financial advice. Trading stocks can lose you everything you put in.
