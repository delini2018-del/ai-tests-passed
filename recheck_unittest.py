"""more-itertools' official test command is `python -m unittest`, which also runs the doctests in recipes.py
(pytest does not). Re-run every pytest survivor under unittest; anything that now fails was really caught."""
import ast, glob, json, os, subprocess, sys
from mutate import apply
work = "work/mibase"
R = [json.loads(l) for f in glob.glob("results/more_itertools_mutants_*.jsonl") for l in open(f)]
out = {}
for r in R:
    if r["failed"] or r["crashed"] or r["timeout"]: continue
    mod, i, kind, j = r["key"].split(":"); src = open(f"libs/more-itertools/{mod}").read()
    new, _ = apply(ast.parse(src), (int(i), kind, int(j)))
    open(f"{work}/{mod}", "w").write(new)
    try:
        p = subprocess.run([sys.executable, "-m", "unittest", "tests.test_recipes"], cwd=work, capture_output=True, text=True, timeout=300,
                           env={**os.environ, "PYTHONPATH": os.path.abspath(work)})
        killed = p.returncode != 0
    except subprocess.TimeoutExpired:
        killed = True
    open(f"{work}/{mod}", "w").write(src)
    out[r["key"]] = killed; print(r["key"], killed, flush=True)
json.dump(out, open("results/more_itertools_survivors_unittest.json", "w"), indent=1)
