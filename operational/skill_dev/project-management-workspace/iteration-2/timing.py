#!/usr/bin/env python3
"""Record one run's usage: timing.py <eval-id> <with|without> <tokens> <duration_ms>"""
import glob, json, sys
e, c, tok, ms = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
d = glob.glob("eval-%s-*/%s_skill/run-1" % (e, c))[0]
json.dump(dict(total_tokens=tok, duration_ms=ms, total_duration_seconds=round(ms / 1000, 1)), open(d + "/timing.json", "w"))
print(d, tok, ms)
