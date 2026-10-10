# Chapter 11: Know When the Team Has No Edge

[`stop_rules.json`](../../stop_rules.json) holds four thresholds. [`retire.py`](../../retire.py) locks them in the ledger, then rules on every strategy: `CONTINUE`, `REVISE`, `RETIRE` or `KEEP RUNNING`. [`pullback-v2.json`](pullback-v2.json) waits in this folder until the step that adds it.

This page runs on the made-up DEMO stock with no key. `retire.py` reads the cap from your signed `mandate.json`, so Chapter 5's copy has to be in the folder.

## Lock, then look

```bash
python retire.py lock
python walkforward.py DEMO
python ledger.py add cards/DEMO.json
python retire.py
```

```text
thresholds locked 12e88a0e5b75
```

```text
breakout-v1 DEMO  CONTINUE     passed every threshold
pullback-v1 DEMO  REVISE       made money, lost to the benchmark
bounce-v1   DEMO  RETIRE       net $-64.63
```

The order matters. Cards filed before a lock get no verdict, which is why the Chapter 8 cards are filed again here.

## Move the goalposts

In `stop_rules.json`, change `"retire_if_net_usd_below": 0` to `-100` and ask again.

```text
REFUSED: stop_rules.json changed after it was locked
  locked  12e88a0e5b75
  on disk 4f0babcfc5cd
  put the file back, or lock the new one and rerun the test
```

Put the `0` back.

## Act on the verdicts

Bounce is retired. Pullback gets a second version, and its first is retired too. The book has you type the new rule file. Here it's a copy.

```bash
mkdir strategies/retired
mv strategies/bounce-v1.json strategies/retired/
mv strategies/pullback-v1.json strategies/retired/
cp chapters/11-retire-what-loses/pullback-v2.json strategies/
```

A new lineup gets its own lock, test and verdicts. Run the four commands from the top of this page again.

```text
breakout-v1 DEMO  CONTINUE     passed every threshold
pullback-v2 DEMO  CONTINUE     passed every threshold
```

Then check that every rule still matches the file it traded as.

```bash
python ledger.py rules
```

```text
breakout-v1: traded as d0c3884fe3c8, same file
pullback-v1: traded as f6b1a1663326, retired, same file
bounce-v1: traded as c730e46ad6e4, retired, same file
pullback-v2: traded as 937e698b4873, same file
```

## Your stock, and your own trades

With bars saved by Chapter 8's `live.py` line, put your own symbol through the same door.

```bash
python walkforward.py XYZ
python ledger.py add cards/XYZ.json
python retire.py
```

The judge prints its DEMO lines again and adds one for each strategy on your stock. Act on those for Monday, with the same file moves as above.

Once you have closed trades of your own, it adds lines marked `yours`. A `yours` line is judged on trade count, net and drawdown only. The benchmark test applies to past-markets cards, so a `yours` line is never `REVISE`. Under ten closed trades it reads `KEEP RUNNING`.

Done is one `RETIRE` acted on, one `REFUSED`, and a `strategies/` folder holding only the rules the swarm should trade on Monday.
