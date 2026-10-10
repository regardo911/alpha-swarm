# Chapter 8: Prove the Edge Without Fooling Yourself

[`walkforward.py`](../../walkforward.py) runs every rule file in `strategies/` over past prices. It tunes on one stretch of days, scores on the next, and counts only the days the tuning never saw.

```bash
python walkforward.py DEMO
```

```text
DEMO: untouched days 2021-12-22 to 2023-11-27
BENCH buy and hold, same days: +21.6%
strategy      net trades wins  maxDD sharpe    t  cost$ beat?
breakout-v1 +37.0%    18   13   8.2%   1.43  2.0  21.65 YES
pullback-v1  +8.8%    12    8  10.6%   0.48  0.7  12.46 no
bounce-v1    -6.5%    17    7  27.2%  -0.24 -0.3  17.67 no
breakout-v1: 20 signals, 2 never filled
pullback-v1: 14 signals, 2 never filled
bounce-v1: 18 signals, 1 never filled
saved cards/DEMO.json
```

Read that table for its columns, and for nothing else. DEMO and BENCH are made-up symbols whose prices come from a formula, built so the three setups would land in three different places. It tells you nothing about a real stock.

Add a strategy's name and you get each round's tuned result next to its untouched one.

```bash
python walkforward.py DEMO bounce-v1
```

```text
bounce-v1 window by window
untouched from  lookback   tuned  untouched
2021-12-22             4   -2.4%     +19.2%
2022-06-16             2  +43.8%     -12.3%
2022-12-09             3  +15.2%      -8.4%
2023-06-05             3   -7.2%      -2.3%
tuned on the latest 252 days: lookback 2
```

File the cards, and the scoreboard grows a third board.

```bash
python ledger.py add cards/DEMO.json
python ledger.py score
```

```text
PAST MARKETS        trades beat?  net $ per 1,000
  breakout-v1 DEMO      18   YES    370.43
  pullback-v1 DEMO      12    no     88.14
  bounce-v1 DEMO        17    no    -64.63
```

## Your stock against SPY

The first line needs your Alpaca key. It saves six years of daily prices for your symbol and for SPY into `bars/`, and the test then reads those files.

```bash
python live.py XYZ SPY
python walkforward.py XYZ
python ledger.py add cards/XYZ.json
```

Same columns, and the benchmark line now reads `SPY buy and hold, same days`. That table is about your stock, your rules and the real market.

Two ways it can stop. A stock with under 378 trading days behind it ends in `ZeroDivisionError`, or `IndexError` under 252: test an older one. A `KeyError` with a date means SPY's file is missing that day: run the `live.py` line again for both.

Done is three DEMO rows with one `YES`, a `PAST MARKETS` board, and a card for a stock you trade filed under it.
