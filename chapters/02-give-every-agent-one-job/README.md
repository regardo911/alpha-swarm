# Chapter 2: Give Every Agent One Job

Four things land in the folder: the team on one page ([`charter.json`](../../charter.json)), a card for each of the five seats ([`roles/`](../../roles)), the checker that proves they fit together ([`check_charter.py`](../../check_charter.py)), and [`swarm.json`](../../swarm.json), which this folder already carries in its finished Chapter 9 form.

```bash
python check_charter.py
```

```text
5 roles: research > thesis > challenge > risk > execution
chain OK: packet > brief > thesis > verdict > size > order
5 decisions, 0 overlaps
the human keeps:
  turn on live trading
  raise the money cap
  keep, change or drop a strategy
CHARTER OK
```

You're done when that ends in `CHARTER OK`, and a broken copy doesn't: `cp charter.json bad.json`, give thesis the risk seat's `owns` line, and `python check_charter.py bad.json` ends in `CHARTER BROKEN: 1 problem(s)`.

Making it yours needs no keys. Change a sentence on a card in `roles/`. Or, to have a seat return something new, add the field to that seat's `keys` in the charter and to its card together. Then run the checker again.
