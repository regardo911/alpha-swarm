"""models.py - put a model in each seat and hold it to its card.

A seat's reply must be JSON with the keys its charter entry
lists. Anything else raises SeatError, and the desk stops.
"""
import hashlib
import json
import os

import keys

keys.load()                 # model keys come from keys.env too


class SeatError(Exception):
    pass


CALLS = {}


def _script(seat, cfg):
    CALLS[seat] = CALLS.get(seat, 0) + 1
    scene = cfg.get("scene", "first")
    tail = "" if CALLS[seat] == 1 else f"-{CALLS[seat]}"
    path = f"fixtures/seats/{scene}/{seat}{tail}.json"
    if not os.path.exists(path):
        path = f"fixtures/seats/first/{seat}.json"
    return open(path).read(), 0, 0


def _openai(card, body, model):
    from openai import OpenAI
    r = OpenAI().responses.create(
        model=model, instructions=card, input=body)
    return r.output_text, r.usage.input_tokens, \
        r.usage.output_tokens


def _anthropic(card, body, model):
    from anthropic import Anthropic
    r = Anthropic().messages.create(
        model=model, max_tokens=1200, system=card,
        messages=[{"role": "user", "content": body}])
    return r.content[0].text, r.usage.input_tokens, \
        r.usage.output_tokens


def ask(seat, payload, cfg, charter):
    spec = cfg["seats"][seat]
    card = open(f"roles/{seat}.md").read()
    body = json.dumps(payload)
    try:
        if spec["provider"] == "script":
            text, t_in, t_out = _script(seat, cfg)
        elif spec["provider"] == "openai":
            text, t_in, t_out = _openai(card, body,
                                        spec["model"])
        elif spec["provider"] == "anthropic":
            text, t_in, t_out = _anthropic(card, body,
                                           spec["model"])
        else:
            raise SeatError(f"{seat}: unknown provider")
        text = text.strip().removeprefix("```json")
        reply = json.loads(text.strip("`\n "))
    except SeatError:
        raise
    except Exception as err:
        raise SeatError(f"{seat}: no usable reply ({err})")
    keys = next(r["keys"] for r in charter["roles"]
                if r["id"] == seat)
    missing = [k for k in keys if k not in reply]
    if missing:
        raise SeatError(f"{seat}: reply is missing {missing}")
    usage = {"provider": spec["provider"],
             "model": spec["model"], "in": t_in, "out": t_out,
             "card": hashlib.sha256(
                 card.encode()).hexdigest()[:12]}
    return reply, usage
