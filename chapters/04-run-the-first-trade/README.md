# Chapter 4: Run the Swarm's First Trade

[`models.py`](../../models.py) puts something in each seat and checks what comes back. [`swarm.py`](../../swarm.py) sends one idea down the line. The replies in [`fixtures/seats/`](../../fixtures/seats) stand in for models, so the first run costs nothing and says the same thing every time.

## The call

```bash
python swarm.py packets/P-0390dac823.json
```

```text
decision D-f01824fc  DEMO
  thesis     buy at 70.96 on breakout-v1
  challenge  PASS, 2 objection(s)
  risk       REDUCE $80
  order      buy 1 DEMO limit 70.96 day
  status     RISK_APPROVED
saved runs/D-f01824fc.json
```

DEMO is the practice stock, so the trade is made up and the plumbing is real. Open `runs/D-f01824fc.json` to read what each seat said.

## A seat that lies

In `swarm.json`, change `"scene": "first"` to `"scene": "broken"` and run the same command. The `broken` thesis cites `N9`, a headline the packet doesn't hold.

```text
decision D-9508a327  DEMO
  thesis     buy at 70.96 on breakout-v1
  status     NO_ORDER
  error      thesis: unsupported claim, cites ['N9']
saved runs/D-9508a327.json
```

Put the scene back to `first`. The chapter is done when the first run says `RISK_APPROVED` and this one says `NO_ORDER`.

## Real models, your packet

Install your provider's package and add its key to `keys.env`: `OPENAI_API_KEY=your-key`, or the `anthropic` package and `ANTHROPIC_API_KEY=your-key`.

```bash
python -m pip install openai
```

In `swarm.json`, give each of the four model seats a provider and an exact model id. Copy the id from your provider's own model list.

```json
    "research": {"provider": "openai", "model": "<id>"},
```

Then run the desk on the packet you saved in Chapter 3.

```bash
python swarm.py packets/P-<yours>.json
```

You get a trade call your own models argued out. Its status line reads `RISK_APPROVED` (with an order), `TOO_SMALL`, `REJECTED`, `NO_IDEA`, or `NO_ORDER` with an error. All five are the desk working.

Don't skip the last step. Save your seating with `cp swarm.json swarm.real.json`, set the four seats back to `{"provider": "script", "model": "none"}`, and run the first command on this page again. Every practice drill from here to Chapter 11 stands on that scripted call.
