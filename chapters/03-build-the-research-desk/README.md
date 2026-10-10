# Chapter 3: Build the Research Desk on Your Machine

A stock symbol goes in, and one frozen file of numbered, sourced facts comes out.

| File | Its job |
|---|---|
| [`make_fixture.py`](../../make_fixture.py) | builds the practice stock |
| [`strategies/`](../../strategies) | three setups, one rule file each |
| [`setups.py`](../../setups.py) | the one copy of every entry and exit rule |
| [`packet.py`](../../packet.py) | freezes a stock's facts, scans your watchlist |
| [`keys.py`](../../keys.py), [`live.py`](../../live.py) | real prices and headlines, on your keys |

## The practice stock first

DEMO is made up. Its prices come from a formula, so the numbers below are the numbers on your screen.

```bash
python make_fixture.py
python packet.py DEMO --fixture
```

```text
DEMO as of 2023-11-27T21:00:00Z
  F1  Last close 70.75 on 2023-11-27
  F2  Highest high of the prior 20 days 70.37
  F3  5-day change +1.1%
  F4  20-day average close 68.65
  F5  Average daily dollar volume 51,008,138
  F6  Second source matches 29 of 30 closes
  X1  FLAG sources disagree on 2023-11-23: 70.25 vs 70.67
  S1  breakout-v1 fired, entry limit 70.96
  N1  DEMO raises full-year sales outlook (Fixture Wire)
  N2  DEMO opens second plant ahead of plan (Fixture Daily)
  N3  Supplier warns of parts delays into DEMO (Fixture Wire)
11 facts, 6 sources, 1 flag(s)
setups fired: ['breakout-v1']
saved packets/P-0390dac823.json
```

`S1` is the trade idea. If your last line names a different packet, your Python is older than 3.12. [BOOK-FIXES.md](../../BOOK-FIXES.md) has the fix.

## Your own stock

Two free accounts: an Alpaca practice account and a Massive key.

```bash
python -m pip install alpaca-py==0.44.0
cp keys.env.example keys.env
```

Put your three keys in `keys.env`. Then open `swarm.json` and replace `"DEMO"` in the watchlist with five to ten symbols you follow, each under $100 a share.

```bash
python packet.py scan
python packet.py XYZ
```

The scan takes seconds and prints one line per stock: the last finished day, the close, and the setup that fired or `no setup`. Pick a symbol where something fired and build its packet, your symbol in place of `XYZ`. That takes about half a minute and prints the DEMO shape with your stock's numbers in it. Keep the file name it prints. Chapter 4 runs on it.

You're done when a packet for a stock you watch sits in `packets/` and every fact in it has an id and a source.

## If it stops

| You see | It means |
|---|---|
| `KeyError: 'APCA_API_KEY_ID'` | `keys.env` is missing, misnamed or in another folder |
| `Massive: too many calls this minute` | you ran it twice quickly. Wait a minute |
| `Massive: your plan does not cover that date` | Massive was asked for a day newer than the free plan covers |
