# Chapter 6: Make Agents Disagree Before Money Moves

One new file, [`gate.py`](../../gate.py): one round of argument, a clock, a price check and the hard limits. `swarm.py` uses it the moment it's in the folder, so here the gate has been on since your first run. The Chapter 4 output is the same either way.

Six drills, all on the made-up DEMO stock, none needing a key. Each is the Chapter 4 command with one thing changed.

| Change | Then run | It ends |
|---|---|---|
| `"scene": "rework"` in `swarm.json` | `python swarm.py packets/P-0390dac823.json` | approved, 16 cents cheaper |
| `"scene": "greedy"` | the same | approved, cut to the cap |
| scene back to `first` | add `price=73.10` | `EXPIRED` |
| | add `now=2023-11-29T14:30:00Z` | `EXPIRED` |
| | add `open=3` | `VETOED` |
| | nothing added | `RISK_APPROVED` |

Do run the last one. Chapter 7 loads `runs/D-f01824fc.json`, and it wants the approved call.

## The argument

The `rework` scene has the challenge send the thesis back once. The thesis answers by paying less.

```text
decision D-04fe496f  DEMO
  thesis     buy at 70.80 on breakout-v1
  challenge  PASS, 1 objection(s), after 1 rework
  risk       REDUCE $80
  order      buy 1 DEMO limit 70.80 day
  status     RISK_APPROVED
saved runs/D-04fe496f.json
```

## Four refusals written in code

Greedy risk seat, capped:

```text
  risk       APPROVE $500
  order      buy 1 DEMO limit 70.96 day
  status     RISK_APPROVED
  why        risk asked $500, hard limit gave $100
```

The stock ran:

```text
  status     EXPIRED
  why        price 73.10 is past 72.38, the most this desk chases
```

The idea went stale:

```text
  status     EXPIRED
  why        thesis died 2023-11-28T21:00:00Z
```

The desk is full:

```text
  status     VETOED
  why        3 positions open, hard limit 3
```

## The three numbers are yours

They sit in the `limits` block of `swarm.json`: `max_position_usd`, `max_open_positions` and `max_chase_pct`. Keep the first equal to `cap_usd` in the mandate you signed.

`price=` is a number you type. The morning run in Chapter 12 passes none, so the desk checks the limit against the last close. That stops a trade only when the thesis bid 2% or more under that close. `open=` is different: the morning run fills it in from your real holdings.
