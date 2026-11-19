#!/usr/bin/env python3
"""temperature_audit.py : the temperature each configuration was actually sent, and what the provider did with it.

SENT. Every per-call log record of runs 259 (logs/), 261 (logs/, g_logs/) and 263 (logs/) under AI_ETHICS/runs/run*/
carries the temperature the harness put in the request body (or_harness.py, anthropic_route.py and
anthropic_route_259.py all copy it into the payload unchanged). Counted per configuration and session.

WHAT THE PROVIDER DID. Responses do not echo temperature, so this is read from what each route allows:
  OpenRouter   the payload carries no require_parameters, so OpenRouter drops a parameter the serving endpoint does not
               list in supported_parameters and the provider's own default applies. The endpoint listings are
               results/openrouter_endpoints_20261118/ (OpenRouter's public /api/v1/models/<id>/endpoints, fetched
               2026-11-18, two to six days after the reads; no listing from the read dates was kept).
                 listed with temperature      -> "accepted"
                 listed without temperature   -> "provider default"
                 provider not in the listing  -> "unverified" (sent, but support cannot be confirmed)
  Anthropic API (direct) a request the API refuses fails with a 400, and every logged call succeeded, so 1.0 was not
               refused. Claude Haiku 5.5 and Sonnet 5.5 refuse any non-default sampling value, Claude Opus 5.5 takes
               none, and Claude Haiku 4.5 with thinking enabled requires 1: on all of these 1.0 is the only value the
               provider allows -> "fixed by provider". (Anthropic's API reference; no direct Haiku 4.5 call without
               thinking was made.)

    python analysis/temperature_audit.py [--ai DIR]   (default banked/)      # writes results/temperature_audit.json
"""
import argparse, collections, glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results", "temperature_audit.json")
LISTINGS = os.path.join(ROOT, "results", "openrouter_endpoints_20261118")
SESSIONS = (("259", "run259", ("logs",)), ("261", "run261", ("logs", "g_logs")), ("263", "run263", ("logs",)))
FIXED_DIRECT = {"claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"}


def listings():
    out = {}
    for f in glob.glob(os.path.join(LISTINGS, "*.json")):
        d = json.load(open(f))["data"]
        by = collections.defaultdict(set)
        for e in d["endpoints"]:
            by[e["provider_name"]].add("temperature" in (e.get("supported_parameters") or []))
        out[d["id"]] = by
    return out


def status_for(rec, lst):
    model, served = rec["model"], rec.get("provider_served")
    if rec["endpoint"].startswith("anthropic "):
        if model in FIXED_DIRECT or (re.search(r"claude-haiku-4[.-]5", model)
                                     and (rec.get("reasoning_on_the_wire") or {}).get("type") == "enabled"):
            return "fixed by provider"
        raise SystemExit(f"REFUSING: no rule for direct {model} with {rec.get('reasoning_on_the_wire')}")
    by = lst.get(model)
    if by is None:
        raise SystemExit(f"REFUSING: no OpenRouter listing saved for {model}")
    if served not in by:
        return "unverified"
    if len(by[served]) > 1:
        raise SystemExit(f"REFUSING: {served} endpoints for {model} disagree on temperature")
    return "accepted" if True in by[served] else "provider default"


def run(ai):
    lst = listings()
    sent = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    status = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for sess, d, subs in SESSIONS:
        for sub in subs:
            for f in sorted(glob.glob(os.path.join(ai, "runs", d, sub, "*_w*.jsonl"))):
                m = re.fullmatch(r"(?:or|an)_(.+)_w\d+\.jsonl", os.path.basename(f))
                if not m:
                    continue
                arm = m.group(1)
                for line in open(f):
                    r = json.loads(line)
                    sent[arm][sess][json.dumps(r.get("temperature"))] += 1
                    if r.get("provider_served") is None:      # a failed call, retried; nothing was served
                        continue
                    status[arm][sess][status_for(r, lst)] += 1
    res = {}
    for arm in sorted(sent):
        temps = {s: dict(c) for s, c in sent[arm].items()}
        stats = {s: dict(c) for s, c in status[arm].items()}
        values = {t for c in temps.values() for t in c}
        kinds = {k for c in stats.values() for k in c}
        res[arm] = {"sent": temps, "status": stats, "temperature": json.loads(values.pop()) if len(values) == 1 else None,
                    "one_status": kinds.pop() if len(kinds) == 1 else None,
                    "changed_between_sessions": len({t for c in temps.values() for t in c}) > 1 or
                                                len({k for c in stats.values() for k in c}) > 1}
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai", default=os.path.join(ROOT, "banked"))
    a = ap.parse_args()
    res = run(a.ai)
    if not res:
        sys.exit(f"REFUSING: no call logs found under {os.path.join(a.ai, 'runs')}")
    body = {"_note": __doc__.split("\n\n")[1], "arms": res}
    if os.path.exists(OUT) and json.load(open(OUT)) != json.loads(json.dumps(body)):
        sys.exit(f"REFUSING: {OUT} exists and differs from the recomputation")
    json.dump(body, open(OUT, "w"), indent=1, sort_keys=True)
    for arm, x in res.items():
        flag = "  CHANGED BETWEEN SESSIONS" if x["changed_between_sessions"] else ""
        print(f"{arm:14} sent {x['temperature']}  {x['one_status'] or x['status']}  sessions {sorted(x['sent'])}{flag}")
