"""Call humanize's public functions on thousands of random inputs (fixed seed) and print every result.
Running this against the original and against a mutant shows whether the mutant changes visible behaviour."""
import datetime as dt, json, math, random, sys
import humanize
rng = random.Random(12345)
def num():
    k = rng.random()
    if k < 0.15: return rng.choice([0, 1, -1, 2, 10, 100, 1000, 1e6, 1e9, 1e12, 1e33, 1e-30, 1e-31, float("inf"), float("-inf"), 0.5, 1.5, 999.5])
    if k < 0.5: return rng.randint(-10**7, 10**7)
    if k < 0.8: return rng.uniform(-1e4, 1e4)
    return 10 ** rng.uniform(-35, 36) * rng.choice([1, -1])
def delta():
    return dt.timedelta(microseconds=int(10 ** rng.uniform(0, 12.5)) * rng.choice([1, 1, 1, -1]))
NOW = dt.datetime(2026, 10, 11, 12, 0, 0)
calls = [
 ("intcomma", lambda: (num(),), {}), ("intcomma", lambda: (rng.randint(-10**9, 10**9),), {"ndigits": None}),
 ("intword", lambda: (num(),), {}), ("apnumber", lambda: (rng.randint(-2, 12),), {}),
 ("ordinal", lambda: (rng.randint(-5, 2000),), {}), ("ordinal", lambda: (rng.randint(0, 200),), {"gender": "female"}),
 ("fractional", lambda: (num(),), {}), ("scientific", lambda: (num(),), {}),
 ("clamp", lambda: (num(),), {"floor": 0.01, "ceil": 1000}), ("metric", lambda: (num(),), {}),
 ("naturalsize", lambda: (abs(num()) if rng.random() < .9 else num(),), {}), ("naturalsize", lambda: (rng.randint(0, 10**15),), {"binary": True}),
 ("naturalsize", lambda: (rng.randint(0, 10**15),), {"gnu": True}),
 ("naturallist", lambda: ([str(i) for i in range(rng.randint(0, 5))],), {}),
 ("naturaldelta", lambda: (delta(),), {}), ("naturaldelta", lambda: (delta(),), {"minimum_unit": "milliseconds"}),
 ("naturaldelta", lambda: (delta(),), {"minimum_unit": "microseconds"}), ("naturaldelta", lambda: (delta(),), {"months": False}),
 ("naturaltime", lambda: (NOW - delta(),), {"when": NOW}), ("naturaltime", lambda: (NOW + delta(),), {"when": NOW, "future": True}),
 ("naturaltime", lambda: ((NOW - delta()).replace(tzinfo=dt.timezone.utc),), {"when": NOW.replace(tzinfo=dt.timezone.utc)}),
 ("precisedelta", lambda: (delta(),), {}), ("precisedelta", lambda: (delta(),), {"minimum_unit": "microseconds"}),
 ("precisedelta", lambda: (delta(),), {"minimum_unit": "hours", "format": "%0.2f"}),
 ("precisedelta", lambda: (delta(),), {"suppress": ["days"]}),
 ("naturalday", lambda: (dt.date.today() + dt.timedelta(days=rng.randint(-3, 3)),), {}),
]
def edges():
    """Hand-picked boundary inputs: the kind of cases a careful human tester writes."""
    td = dt.timedelta
    ds = [td(microseconds=u) for u in (0, 1, 999, 1000, 1001, 999999, 1000000)]
    ds += [td(seconds=s) for s in (1, 59, 60, 61, 119, 120, 3599, 3600, 3601, 86399, 86400)]
    ds += [td(days=d) for d in (1, 2, 29, 30, 31, 32, 45, 60, 152, 153, 180, 364, 365, 366, 730, 3650)]
    ds += [td(days=d, hours=h, minutes=m, seconds=s, microseconds=u) for d, h, m, s, u in
           [(0, 0, 0, 1, 500000), (0, 0, 1, 30, 0), (0, 1, 30, 0, 0), (1, 12, 0, 0, 0), (400, 0, 0, 0, 1500)]]
    r = []
    for d in ds:
        for kw in ({}, {"minimum_unit": "milliseconds"}, {"minimum_unit": "microseconds"}, {"months": False}):
            r.append(("naturaldelta", (d,), kw))
        for kw in ({}, {"minimum_unit": "microseconds"}, {"minimum_unit": "milliseconds"}, {"format": "%0.2f"},
                   {"minimum_unit": "minutes", "format": "%0.1f"}, {"suppress": ["days"]}, {"minimum_unit": "days"}):
            r.append(("precisedelta", (d,), kw))
        r.append(("naturaltime", (NOW - d,), {"when": NOW})); r.append(("naturaltime", (NOW + d,), {"when": NOW}))
    r.append(("naturaltime", (NOW,), {"when": NOW}))
    aware = dt.datetime.now(dt.timezone.utc) - td(hours=3)
    r.append(("naturaltime", (aware,), {}))
    for v in (0, 1, -1, 0.5, 1e33, 9.99e32, 1e-30, 1e-31, 999, 1000, 1001, 1e6, float("inf"), float("-inf"), float("nan"), 2**64):
        for f in ("intcomma", "intword", "scientific", "fractional", "metric", "naturalsize"):
            r.append((f, (v,), {}))
        r.append(("clamp", (v,), {"floor": 1, "ceil": 1000}))
    for loc in ("fr_FR", "de_DE", "es_ES"):
        r.append(("__locale__", (loc,), {}))
        for v in (1, 2, 21, 1234567.891, 1000):
            r.append(("ordinal", (v,), {})); r.append(("ordinal", (v,), {"gender": "female"})); r.append(("intcomma", (v,), {}))
        r.append(("__locale__", (None,), {}))
    return r
out = []
if len(sys.argv) > 2 and sys.argv[2] == "edges":
    for name, a, kw in edges():
        if name == "__locale__":
            try: humanize.i18n.activate(a[0]) if a[0] else humanize.i18n.deactivate(); out.append("loc ok")
            except Exception as e: out.append("loc EXC:" + type(e).__name__)
            continue
        try: res = repr(getattr(humanize, name)(*a, **kw))
        except Exception as e: res = "EXC:" + type(e).__name__
        out.append(res)
    print(json.dumps(out)); sys.exit()
for _ in range(int(sys.argv[1]) if len(sys.argv) > 1 else 300):
    for name, args, kw in calls:
        a = args()
        try: r = repr(getattr(humanize, name)(*a, **kw))
        except Exception as e: r = "EXC:" + type(e).__name__
        out.append(r)
print(json.dumps(out))
