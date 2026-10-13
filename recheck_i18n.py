"""Re-run the 58 humanize survivors against the project's i18n tests too (they need compiled translations)."""
import ast, glob, json, os
from mutate import apply, run_tests
os.environ["SRC"] = "src"; work = "work/base"
R = [json.loads(l) for f in glob.glob("results/humanize_mutants_*.jsonl") for l in open(f)]
out = {}
for r in R:
    if r["failed"] or r["crashed"] or r["timeout"]: continue
    mod, i, kind, j = r["key"].split(":"); src = open(f"libs/humanize/{mod}").read()
    new, _ = apply(ast.parse(src), (int(i), kind, int(j)))
    open(f"{work}/{mod}", "w").write(new)
    res = run_tests(work, ["tests/test_i18n.py"], 60)
    open(f"{work}/{mod}", "w").write(src)
    out[r["key"]] = res; print(r["key"], len(res["failed"]), res["crashed"])
json.dump(out, open("results/humanize_survivors_i18n.json", "w"), indent=1)
