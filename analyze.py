"""Summaries and charts for the article."""
import json, glob, random, collections, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12, "axes.spines.top": False, "axes.spines.right": False})
INK, RED, BLUE, GREY, GREEN, AMB = "#1f2937", "#c2410c", "#2563eb", "#cbd5e1", "#15803d", "#e9a23b"
os.makedirs("charts", exist_ok=True)
S = {}
COV = {"humanize": 0.99, "more_itertools": 0.99}   # measured: 98-100% (humanize core modules), 99% (recipes.py)
for lib in ["humanize", "more_itertools"]:
    R = [json.loads(l) for f in glob.glob(f"results/{lib}_mutants_*.jsonl") for l in open(f)]
    extra = {}   # survivors later caught by the rest of the project's official suite
    if lib == "humanize": extra = {k for k, v in json.load(open("results/humanize_survivors_i18n.json")).items() if v["failed"] or v["crashed"]}
    if lib == "more_itertools": extra = {k for k, v in json.load(open("results/more_itertools_survivors_unittest.json")).items() if v}
    for r in R:
        if r["key"] in extra: r["crashed"] = True
    killed = [r for r in R if r["failed"] or r["crashed"] or r["timeout"]]
    by = collections.defaultdict(lambda: [0, 0])
    for r in R: by[r["kind"]][0] += 1; by[r["kind"]][1] += not (r["failed"] or r["crashed"] or r["timeout"])
    nf = [len(r["failed"]) for r in R if r["failed"]]
    S[lib] = dict(mutants=len(R), killed=len(killed), survived=len(R) - len(killed), score=len(killed) / len(R),
                  by_kind={k: dict(n=v[0], survived=v[1]) for k, v in by.items()},
                  killed_by_1=sum(1 for x in nf if x == 1), killed_by_le3=sum(1 for x in nf if x <= 3), killed_with_ids=len(nf),
                  crashed_or_timeout=sum(1 for r in R if r["crashed"] or r["timeout"]))
# test-subset curve (humanize): which mutants would a random fraction of the tests still catch?
R = [json.loads(l) for f in glob.glob("results/humanize_mutants_*.jsonl") for l in open(f)]
I18N = {k for k, v in json.load(open("results/humanize_survivors_i18n.json")).items() if v["failed"] or v["crashed"]}
tests = sorted({t for r in R for t in r["failed"]})
rng = random.Random(0); curve = []
for frac in [0.01, 0.02, 0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0]:
    vals = []
    for _ in range(30):
        keep = set(rng.sample(tests, max(1, int(len(tests) * frac))))
        k = sum(1 for r in R if (set(r["failed"]) & keep) or ((r["crashed"] or r["timeout"]) and not r["failed"]))
        vals.append(k / len(R))
    curve.append((frac, sum(vals) / len(vals)))
S["humanize"]["curve"] = curve; S["humanize"]["tests_that_ever_fail"] = len(tests)
E = {e["key"]: e for e in json.load(open("results/humanize_survivors_edges.json"))}
Rr = {e["key"]: e for e in json.load(open("results/humanize_survivors_random.json"))}
surv_keys = {r["key"] for r in R if not (r["failed"] or r["crashed"] or r["timeout"])} - I18N
conf = {k for k in surv_keys if k in E and ((E[k]["n_diff"] or E[k]["broke_fuzz"]) or (Rr.get(k, {}).get("n_diff")))}
EQUIV = {"src/humanize/lists.py:10:bool:0", "src/humanize/number.py:42:bool:0", "src/humanize/time.py:36:bool:0",
         "src/humanize/number.py:476:compare:0", "src/humanize/number.py:480:compare:0",
         "src/humanize/number.py:880:number:0", "src/humanize/number.py:885:number:0"}
S["humanize"]["survivors_confirmed"] = len(conf); S["humanize"]["survivors_equivalent"] = len(EQUIV & surv_keys)
S["humanize"]["survivors_unresolved"] = len(surv_keys) - len(conf) - len(EQUIV & surv_keys)
S["humanize"]["examples"] = [(E[k]["code"], E[k]["example"]) for k in sorted(conf) if E.get(k, {}).get("example")]
json.dump(S, open("results/summary.json", "w"), indent=1, ensure_ascii=False)

# chart 1: coverage vs mutation score
fig, ax = plt.subplots(figsize=(11, 4.8))
labs = ["humanize\n(841 tests)", "more-itertools recipes\n(199 tests + 9,884 sub-tests)"]
for i, lib in enumerate(["humanize", "more_itertools"]):
    ax.barh(i + 0.2, COV[lib] * 100, height=0.36, color=GREY); ax.barh(i - 0.2, S[lib]["score"] * 100, height=0.36, color=BLUE)
    ax.text(COV[lib] * 100 - 1, i + 0.2, "lines executed by tests: 98–100%" if lib == "humanize" else "lines executed by tests: 99%", ha="right", va="center", fontsize=11)
    ax.text(S[lib]["score"] * 100 - 1, i - 0.2, f"planted bugs caught: {S[lib]['score']*100:.0f}%", ha="right", va="center", color="white", fontsize=11, fontweight="bold")
ax.set_yticks([0, 1], labs); ax.set_xlim(0, 100); ax.invert_yaxis(); ax.set_xlabel("%")
fig.suptitle("The tests touch almost every line. They still miss planted bugs.", x=0.02, ha="left", fontsize=14, color=INK)
fig.tight_layout(); fig.savefig("charts/01_coverage_vs_caught.png", dpi=200); plt.close(fig)

# chart 2: what the humanize survivors turned out to be
h = S["humanize"]; parts = [("Proved to change visible output", h["survivors_confirmed"], RED),
    ("Unresolved: no difference on my probe inputs", h["survivors_unresolved"], AMB), ("Harmless on inspection", h["survivors_equivalent"], GREY)]
fig, ax = plt.subplots(figsize=(11, 2.8)); left = 0
for n, v, c in parts:
    ax.barh(0, v, left=left, color=c, height=0.5); ax.text(left + v / 2, 0, str(v), ha="center", va="center", color="white", fontsize=14, fontweight="bold")
    ax.text(left + v / 2, -0.42, n, ha="center", va="top", fontsize=10.5, color=INK); left += v
ax.set_xlim(0, left); ax.set_ylim(-0.9, 0.4); ax.axis("off")
fig.suptitle(f"The {h['survived']} planted bugs that all 841 humanize tests missed", x=0.02, ha="left", fontsize=14, color=INK)
fig.tight_layout(); fig.savefig("charts/02_survivors.png", dpi=200); plt.close(fig)

# chart 3: more tests, same blind spots
fr, sc = zip(*curve)
fig, ax = plt.subplots(figsize=(11, 4.8))
ax.plot([f * 100 for f in fr], [s * 100 for s in sc], color=BLUE, lw=3, marker="o")
ax.axhline(sc[-1] * 100, color=RED, ls="--", lw=1.4); ax.text(2, sc[-1] * 100 + 1, f"ceiling with every test: {sc[-1]*100:.0f}%", color=RED, fontsize=11)
ax.set_xscale("log"); ax.set_xticks([1, 2, 5, 10, 20, 50, 100], ["1%", "2%", "5%", "10%", "20%", "50%", "100%"])
ax.set_xlabel("Share of humanize's tests kept (random subsets)"); ax.set_ylabel("Planted bugs caught (%)"); ax.set_ylim(0, 100)
fig.suptitle("Every doubling of the test suite catches fewer new bugs, and 11% escape all of them", x=0.02, ha="left", fontsize=14, color=INK)
fig.tight_layout(); fig.savefig("charts/03_more_tests.png", dpi=200); plt.close(fig)
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("examples", "curve")} for k, v in S.items()}, indent=1))
print(curve)
