# Chapter 10: Put More Money Behind Your Winners

Five rungs: practice at $100 a trade, then live money at $100, $250, $500 and $1,000. [`ladder.json`](../../ladder.json) holds them with the gate numbers, and [`ladder.py`](../../ladder.py) reads your ledger and says whether the next rung is earned. It works out your rung from the `mandate.json` you signed in Chapter 5, and stops at a missing file if you haven't.

## Where you stand

```bash
python ladder.py
```

```text
rung: practice ($100 a trade, practice)
gate               have      need
closed trades      0         >= 20      NOT YET
net $ per trade    0         >= 0.01    NOT YET
drawdown %         0.0       <= 10      pass
unfilled %         0         <= 30      pass
order % of volume  0.0       <= 1.0     pass
ledger hashes      0         == 0       pass
STAY. Still open: closed trades, net $ per trade
```

Those zeros are your own record. Practice-file trades don't count toward a rung.

## What earning it looks like

[`fixtures/record_DEMO.json`](../../fixtures/record_DEMO.json) is twenty made-up closed trades. Hand it to the ladder and watch every gate pass.

```bash
python ladder.py fixtures/record_DEMO.json
```

```text
WHAT IF: fixtures/record_DEMO.json
rung: practice ($100 a trade, practice)
gate               have      need
closed trades      20        >= 20      pass
net $ per trade    1.5       >= 0.01    pass
drawdown %         4.3       <= 10      pass
unfilled %         10        <= 30      pass
order % of volume  0.01      <= 1.0     pass
ledger hashes      0         == 0       pass
EARNED: first money, $100 a trade, live
to take it, you sign mandate.json
```

Write your own what-if the same way: a `nets` list of dollars per trade and an `extra` block.

## Signing for live money

Three edits, and no file in the book makes them for you.

1. In `mandate.json`, set `"mode": "live"` and the date.
2. In `keys.env`, add the second pair of keys from your live Alpaca account, under `APCA_LIVE_API_KEY_ID` and `APCA_LIVE_API_SECRET_KEY`.
3. When you climb a rung, put the same number in two places: `cap_usd` in `mandate.json` and `max_position_usd` in `swarm.json`.

Don't make the first edit because of a good week. Make it when `python ladder.py` says `EARNED` on your own trades.

## Will your broker sell you a slice?

This needs your Alpaca practice keys. It sends a practice order for $25 of a stock from one of your packets, at a limit 10% under the last close.

```bash
python broker.py slice packets/P-<yours>.json 25
```

If the broker takes it, you see the Chapter 5 shape with a fraction of a share in it. If not, one line starting `broker refused:`. Cancel the test with `python broker.py cancel SLICE-<the ten characters>`, and keep your watchlist to stocks priced under your cap until you've seen a slice go through.
