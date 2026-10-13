"""For each surviving mutant: run fuzz_humanize.py on the original and on the mutant; record whether outputs differ."""
import ast, json, glob, os, subprocess, sys, shutil
from mutate import apply
repo, work = "libs/humanize", "work/fuzz"
if not os.path.exists(work): shutil.copytree(repo, work, ignore=shutil.ignore_patterns(".git"))
env = {**os.environ, "PYTHONPATH": os.path.abspath(f"{work}/src")}
MODE = sys.argv[1] if len(sys.argv) > 1 else "random"
def fuzz():
    r = subprocess.run([sys.executable, os.path.abspath("fuzz_humanize.py"), "300", MODE], capture_output=True, text=True, env=env, timeout=600, cwd="/tmp")
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None
base = fuzz(); print("calls per run:", len(base))
R = [json.loads(l) for f in glob.glob("results/humanize_mutants_*.jsonl") for l in open(f)]
out = []
for r in R:
    if r["failed"] or r["crashed"] or r["timeout"]: continue
    mod, i, kind, j = r["key"].split(":"); src = open(f"{repo}/{mod}").read()
    new, _ = apply(ast.parse(src), (int(i), kind, int(j)))
    open(f"{work}/{mod}", "w").write(new)
    try: res = fuzz()
    except subprocess.TimeoutExpired: res = None
    open(f"{work}/{mod}", "w").write(src)
    diffs = None if res is None else [k for k, (a, b) in enumerate(zip(base, res)) if a != b]
    example = None
    if diffs: example = (base[diffs[0]], res[diffs[0]])
    out.append(dict(key=r["key"], line=r["line"], code=r["code"], kind=kind, broke_fuzz=res is None,
                    n_diff=None if diffs is None else len(diffs), example=example))
    print(r["key"], "DIFF" if (diffs or res is None) else "same", example)
json.dump(out, open(f"results/humanize_survivors_{MODE}.json", "w"), indent=1)
