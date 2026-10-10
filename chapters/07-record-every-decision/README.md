# Chapter 7: Record the Strategy That Actually Ran

[`ledger.py`](../../ledger.py) is the longest file in the book. Every step of every decision becomes a row that can't be edited, and one command turns the rows into a scoreboard. [`fixtures/events_DEMO.json`](../../fixtures/events_DEMO.json) is a made-up week of broker events for the made-up stock, so a whole trade can go through before any market opens.

## Load a decision and follow it

```bash
python ledger.py add runs/D-f01824fc.json
python ledger.py add fixtures/events_DEMO.json
python ledger.py trace D-f01824fc
```

The two loads print `6 rows added` and `5 rows added`. Load the run again and it says `already in the ledger`. The trace:

```text
D-f01824fc: 11 rows
  1 evidence     research  1d4256140d925372  P-0390dac823
  2 brief        research  744989739a5f0f6f
  3 thesis       thesis    8de0d22e041d12eb  limit 70.96
  4 challenge    challenge c13ccce14dfae8f0  PASS
  5 risk         risk      571fd6b287139583  REDUCE
  6 decision     execution bcd76b77ab7ce9ee  RISK_APPROVED
  7 submitted    execution 00736db7aa6e256b  buy limit 70.96
  8 new          execution 0c7720bc65169281
  9 fill         execution c1ba9d522623a2c7  buy 1 at 70.88
 10 submitted    execution fb172a0316d0e5e9  sell limit 74.10
 11 fill         execution 9a414d4c76beee37  sell 1 at 74.31
strategy breakout-v1@d0c3884fe3c8
```

The characters after the `@` are a fingerprint of the rule file's exact bytes. If yours differ, your `strategies/breakout-v1.json` has different line endings, or no line break at the end.

## Try to change the past

```bash
python ledger.py tamper
python ledger.py verify
```

```text
UPDATE   refused: append-only: no UPDATE
DELETE   refused: append-only: no DELETE
REPLACE  refused: append-only: no DELETE
```

```text
11 rows, 0 with a broken hash
```

Now edit a rule that has already traded. Change `"stop_pct": 0.06` to `0.05` in `strategies/breakout-v1.json` and run `python ledger.py rules`.

```text
breakout-v1: traded as d0c3884fe3c8, CHANGED on disk
  save edits as a new version
```

Change it back, and the same command says `same file`.

## The scoreboard

```bash
python ledger.py score
```

```text
YOUR TRADES         closed  wins     net $
  none yet
PRACTICE FILE       closed  wins     net $
  breakout-v1            1     1      3.43
```

## Your own order

No keys needed. The ledger reads the files `swarm.py` and `broker.py` already saved.

```bash
python ledger.py add runs/D-<yours>.json
python ledger.py add orders/D-<yours>.json
python ledger.py trace D-<yours>
```

Your trace stops at a `submitted` row until the order fills. After `python broker.py check` picks up the fill, add the order file again and only the new rows go in. A wiring test from Chapter 5 has nothing to load.

Done is eleven practice rows from the fill back to the packet, three refusals, zero broken rows, and your own decision traced as far as the order you sent.
