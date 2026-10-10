# Chapter 5: Connect the Swarm to the Stock Market

One file and one signature. [`broker.py`](../../broker.py) sends the order the desk approved, reads back what the broker now holds, and prints `MATCH` when the two agree.

## Sign first

[`mandate.json`](mandate.json) lives in this folder because copying it in is the signature.

```bash
cp chapters/05-connect-to-your-broker/mandate.json .
```

Put your name and today's date in the last two lines of the copy, and leave `"mode": "practice"` alone. Until that file is in the folder, `broker.py` stops at a `FileNotFoundError` naming `mandate.json`. So do `ladder.py`, `retire.py` and `daily.py` later on.

## The evening, in order

Every step needs `alpaca-py` installed and a `keys.env`. Steps 1, 2 and 4 to 7 reach Alpaca on your practice keys. Step 3 is refused on your own machine before anything is sent, so the example key file works for it as it ships.

1. Ask the broker what time it is.

   ```bash
   python broker.py clock
   ```

   It prints whether the market is open, and the next open and close in New York time.

2. Check the account is alive.

   ```bash
   python broker.py account
   ```

   You want a status of `ACTIVE` and a cash figure. Unauthorized or forbidden means the keys are wrong, or they're live keys. `KeyError: 'APCA_API_KEY_ID'` means `keys.env` isn't in this folder.

3. Watch two refusals. In your `mandate.json`, change `"cap_usd": 100` to `"cap_usd": 50`, then try to send the practice decision from Chapter 4.

   ```bash
   python broker.py send runs/D-f01824fc.json
   ```

   ```text
   REFUSED here: $70.96 is over the signed cap of $50
   ```

   Put the cap back to 100 and run the same line.

   ```text
   REFUSED here: a practice-file decision, not a real stock
   ```

   DEMO is made up, so it never leaves your machine.

4. Send a real one: the run the swarm approved on your own stock or, if nothing fired today, the wiring test. The test bids for one share at 10% under the last close, where it should sit and wait. Use a stock under about $110 a share, or your own cap refuses it.

   ```bash
   python broker.py send runs/D-<yours>.json
   python broker.py test packets/P-<yours>.json
   ```

   Either way, the shape is this.

   ```
   order id   <a long id from the broker>
   status     accepted, filled 0
   sent       buy 1 XYZ limit <your limit>
   broker has buy 1 XYZ limit <your limit>
   MATCH
   saved orders/<your decision>.json
   ```

5. Send it again, word for word. Same order id, same `MATCH`, and one new line on top: `already at the broker, not sent again`.

6. Ask where it is, any time.

   ```bash
   python broker.py check <your decision>
   ```

7. If you sent the wiring test, cancel it. `cancel` is for a decision that's waiting at the broker.

   ```bash
   python broker.py cancel TEST-<the ten characters>
   ```

   A real swarm order stays. It's Monday's first trade.

## Done means

The broker gave you an order id, the screen said `MATCH`, and the second send was not sent. On a weekend the order waits in the broker's queue until Monday's open.
