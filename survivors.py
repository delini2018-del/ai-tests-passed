"""Print every surviving mutant: original line and mutated line, for manual review."""
import ast, json, glob, sys
from mutate import apply
lib, repo = sys.argv[1], sys.argv[2]
R = [json.loads(l) for f in glob.glob(f"results/{lib}_mutants_*.jsonl") for l in open(f)]
for r in sorted(R, key=lambda r: (r["module"], r["line"] or 0)):
    if r["failed"] or r["crashed"] or r["timeout"]: continue
    mod, i, kind, j = r["key"].split(":"); src = open(f"{repo}/{mod}").read()
    new, line = apply(ast.parse(src), (int(i), kind, int(j)))
    o = ast.unparse(ast.parse(src)).splitlines(); n = new.splitlines()
    diff = [(a, b) for a, b in zip(o, n) if a != b]
    print(f"{r['key']} | L{r['line']} | {kind}\n   - {diff[0][0].strip() if diff else '?'}\n   + {diff[0][1].strip() if diff else '?'}")
