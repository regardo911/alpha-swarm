# Chapter 12: Put the Swarm to Work at Monday's Open

[`daily.py`](../../daily.py) ties nine of the weekend's files into three commands. `morning` runs before the open: the record, exits, then new ideas. `check` asks the broker where every order is. `week` is the review you run yourself. The scheduler files are [`com.alphaswarm.morning.plist`](../../com.alphaswarm.morning.plist) for a Mac and [`morning.sh`](../../morning.sh) for Linux.

`morning` and `check` are the whole desk on your own accounts: Alpaca practice keys, a Massive key, a model key, and the mandate you signed in Chapter 5.

## Make it yours first

Three edits to `swarm.json` before anything goes on a schedule.

- Your watchlist: five to ten stocks you'd want to own, each priced under your cap, and no `DEMO`.
- Your seats: copy your four seat lines back from `swarm.real.json`, and only those four lines. Keep the `rates` and `costs` blocks already in this `swarm.json`: without them the morning run opens no new trades. Give each seated model its own entry in `rates` while you're there (Chapter 9).
- Your limits: the three numbers from Chapter 6, set where you're comfortable leaving them while you're not looking.

## Run it by hand once

```bash
python daily.py morning
```

On a weekend you get the short version, with real dates in it.

```
morning run <today's date and time>
market closed today, next open <Monday> 09:30:00-04:00
```

A file in `sheets/` now holds those two lines, under a UTC date, and `python ledger.py verify` counts one more row. `KeyError: 'APCA_API_KEY_ID'` means `keys.env` isn't in the folder the command ran from.

## Mac

Open `com.alphaswarm.morning.plist` and replace `/Users/you` with your own home folder in all four places. It fires at 8:30 on your computer's clock. Outside New York time, change the `8` and the `30`.

```bash
cp com.alphaswarm.morning.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) \
    ~/Library/LaunchAgents/com.alphaswarm.morning.plist
launchctl kickstart gui/$(id -u)/com.alphaswarm.morning
```

The last line fires it once, right now. To take the job off the schedule: `launchctl bootout gui/$(id -u)/com.alphaswarm.morning`.

## Linux

Put your own path in `morning.sh`, make it runnable with `chmod +x morning.sh`, then run `crontab -e` and add one line.

```
30 8 * * 1-5 /home/you/alpha-swarm/morning.sh
```

Cron waits for 8:30 on a weekday. Run `./morning.sh` by hand tonight to prove the script and its paths.

## Windows

Build yours from step 2 of the chapter, fire it once, and look for the sheet. The book gives the parts of a `schtasks /create` line from Microsoft's documentation, and its author had no Windows machine to run it on, so this folder ships no file for it.

## Did it fire?

```bash
ls sheets/
python ledger.py verify
```

The sheet's first line carries the time of a run you didn't start, and the row count is one higher. If the time hasn't moved, open `morning.log`, where both scheduler files send everything the run prints.

For the afternoon, make a second entry with `check` in place of `morning` everywhere, the label and the file name included, at a time after the 4:00 New York close.

## Every week

```bash
python daily.py week
```

It prints the scoreboard, the ladder and the verdicts from your own files, with no broker call, but `alpaca-py` has to be installed because `daily.py` imports the broker file. On the practice folder as Chapter 11 leaves it, the made-up DEMO stock ends like this:

```text
STAY. Still open: closed trades, net $ per trade

breakout-v1 DEMO  CONTINUE     passed every threshold
pullback-v2 DEMO  CONTINUE     passed every threshold
```

Then make your three calls: sign for a rung or don't, move a retired rule's file, write the next version of a revised one. Most weeks none of it applies.
