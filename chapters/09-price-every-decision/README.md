# Chapter 9: Know What Every Decision Costs

[`costs.py`](../../costs.py) prices one decision row by row and marks every row `measured` or `assumed`. The prices it multiplies by live in three blocks at the bottom of [`swarm.json`](../../swarm.json): `rates`, `costs` and `lineups`. [`fixtures/tokens_DEMO.json`](../../fixtures/tokens_DEMO.json) holds the token counts from one real decision on the author's machine.

## One decision, priced

```bash
python costs.py runs/D-f01824fc.json --record
```

```text
decision D-f01824fc  position $70.96
  model calls measured $  0.0000
    research           $  0.0000
    thesis             $  0.0000
    challenge          $  0.0000
    risk               $  0.0000
  market data assumed  $  0.0000
  broker fees assumed  $  0.0300
  spread      assumed  $  0.0355
  slippage    assumed  $  0.0710
  total                $  0.1364
  break-even move         0.19%
cost row added to the ledger
```

Scripted seats are free, so the model rows are zero. The rest is trading friction on a made-up $70.96 position. `python ledger.py score` now shows the practice trade at 3.29 where it showed 3.43, and `python ledger.py trace D-f01824fc` ends on a new row:

```text
 12 cost         execution 3f13860c63e94428  $0.1364
```

## Four ways to seat the desk

```bash
python costs.py lineups fixtures/tokens_DEMO.json
```

```text
lineup        $/decision  break-even move at
                          $100    $250    $500    $1000
all-small     $0.0061     0.19%   0.16%   0.16%   0.15%
big-skeptic   $0.0254     0.21%   0.17%   0.16%   0.16%
big-risk      $0.0101     0.19%   0.17%   0.16%   0.15%
all-large     $0.0615     0.24%   0.19%   0.17%   0.16%
```

The `small` and `large` rates behind that table are round example numbers, there so the practice output has something to multiply.

## Your own bill

Two instructions, and the order matters.

1. Add your rates before your first run with real models. Each model you seated gets one entry in `rates`, named with its exact model id, at the dollars per million tokens on your provider's pricing page. A seat whose model has no entry is priced at `$0.0000`, and its row still reads `measured`.
2. Record each decision's cost once, after the rates are in. Run `--record` a second time after a rate or a cost setting has changed and the ledger takes a second cost row. The scoreboard subtracts both.

```bash
python costs.py runs/D-<yours>.json --record
```

If the command stops at `D-<yours>: record the run first`, load the run with `python ledger.py add runs/D-<yours>.json` and try again.

To read the lineup table at your own prices, put your small model's rates under `small` and your large model's under `large`. You can also hand `lineups` your own counts: a file with one `[tokens in, tokens out]` pair per seat, added up from the `usage` block of any run file.

No key needed. You're done when your own decision has a total and a break-even move, and its trace ends in a `cost` row.
