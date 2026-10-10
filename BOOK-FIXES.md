# Book fixes

One entry. The book's 44 files are here byte for byte, so the fix is which Python you run them on.

## Chapter 2: "Python 3 and a number" has to be 3.12 or newer

Chapter 2 says you want `python --version` to print "Python 3 and a number". On 3.12, 3.13 and 3.14, every number in the book comes out on your screen. On 3.11 and older the practice packet gets a different name. Python 3.12 changed how `sum()` adds decimals, so one figure in the packet moves in its last digit.

The same files on Python 3.11.15:

```
$ python packet.py DEMO --fixture
...
saved packets/P-8ce9a7ce2e.json
```

The book prints `P-0390dac823`, so Chapter 4's `python swarm.py packets/P-0390dac823.json` ends in `FileNotFoundError`. Every decision number is built from the packet's, and the book's `D-f01824fc` comes out as `D-9259f204`. Chapter 7's practice week names `D-f01824fc` inside the file, so it stops loading:

```
$ python ledger.py add fixtures/events_DEMO.json
D-f01824fc: record the run first
```

From Chapter 7 on, the practice trade is missing from the scoreboard.

The fix: build the folder's Python from 3.12 or newer, for example `python3.12 -m venv .venv`. Then delete `packets/`, `runs/` and `ledger.db`, and start again from `python packet.py DEMO --fixture`. A Mac's own `python3` can be older than that, so check first.
