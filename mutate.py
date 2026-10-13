"""A small, dependency-free mutation tester.
Plants one small bug at a time ("mutant") in a real library's source, runs the library's own test suite,
and records which tests (if any) fail. A mutant that no test notices "survives".
Operators: comparison flips (<,<=,>,>=,==,!=,in,is), arithmetic swaps (+,-,*,/,//,%), integer constants +/-1,
True<->False, and<->or, dropping a `not`, and `return x` -> `return None`."""
import ast, copy, json, os, random, re, shutil, subprocess, sys, time

CMP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq,
       ast.In: ast.NotIn, ast.NotIn: ast.In, ast.Is: ast.IsNot, ast.IsNot: ast.Is}
BIN = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Div, ast.Div: ast.Mult, ast.FloorDiv: ast.Div, ast.Mod: ast.Mult}

def sites(tree):
    """Every (node index, operator name, description) where a mutation can be applied."""
    out = []
    docstrings = {id(n.body[0].value) for n in ast.walk(tree) if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef))
                  and n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
    for i, n in enumerate(ast.walk(tree)):
        if isinstance(n, ast.Compare):
            for j, op in enumerate(n.ops):
                if type(op) in CMP: out.append((i, "compare", j))
        elif isinstance(n, ast.BinOp) and type(n.op) in BIN: out.append((i, "arith", 0))
        elif isinstance(n, ast.AugAssign) and type(n.op) in BIN: out.append((i, "arith", 0))
        elif isinstance(n, ast.Constant) and id(n) not in docstrings:
            if isinstance(n.value, bool): out.append((i, "bool", 0))
            elif isinstance(n.value, int): out.append((i, "number", 0))
        elif isinstance(n, ast.BoolOp): out.append((i, "and_or", 0))
        elif isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not): out.append((i, "drop_not", 0))
        elif isinstance(n, ast.Return) and n.value is not None and not (isinstance(n.value, ast.Constant) and n.value.value is None):
            out.append((i, "return_none", 0))
    return out

def apply(tree, site):
    t = copy.deepcopy(tree); i, kind, j = site
    nodes = list(ast.walk(t)); n = nodes[i]
    if kind == "compare": n.ops[j] = CMP[type(n.ops[j])]()
    elif kind == "arith": n.op = BIN[type(n.op)]()
    elif kind == "bool": n.value = not n.value
    elif kind == "number": n.value = n.value + 1 if n.value != 1 else 0
    elif kind == "and_or": n.op = ast.Or() if isinstance(n.op, ast.And) else ast.And()
    elif kind == "drop_not":
        for p in nodes:
            for f, v in ast.iter_fields(p):
                if v is n: setattr(p, f, n.operand)
                elif isinstance(v, list):
                    for k, x in enumerate(v):
                        if x is n: v[k] = n.operand
    elif kind == "return_none": n.value = ast.Constant(None)
    return ast.unparse(ast.fix_missing_locations(t)), getattr(n, "lineno", None)

def run_tests(workdir, tests, timeout):
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rf", "--tb=no", "--color=no", *tests],
                           cwd=workdir, capture_output=True, text=True, timeout=timeout,
                           env={**os.environ, "PYTHONPATH": os.path.abspath(os.path.join(workdir, os.environ.get("SRC", "")))})
        out = re.sub(r"\x1b\[[0-9;]*m", "", r.stdout)
        failed = sorted(set(m.split(" - ")[0] for m in re.findall(r"^FAILED (.+)$", out, re.M)))
        return dict(failed=failed, crashed=bool(r.returncode != 0 and not failed), timeout=False, secs=time.time() - t0)
    except subprocess.TimeoutExpired:
        return dict(failed=[], crashed=False, timeout=True, secs=timeout)

if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1])); worker, nworkers = int(sys.argv[2]), int(sys.argv[3])
    lib = cfg["lib"]; work = f"work/{lib}_{worker}"
    if not os.path.exists(work): shutil.copytree(cfg["repo"], work, ignore=shutil.ignore_patterns(".git"))
    os.environ["SRC"] = cfg.get("src", "")
    rng = random.Random(0); jobs = []
    for mod in cfg["modules"]:
        src = open(os.path.join(cfg["repo"], mod)).read(); tree = ast.parse(src)
        for s in sites(tree): jobs.append((mod, s))
    rng.shuffle(jobs); jobs = jobs[:cfg.get("max_mutants", 10**9)]
    out = open(f"results/{lib}_mutants_{worker}.jsonl", "a")
    done = {json.loads(l)["key"] for l in open(out.name)} if os.path.getsize(out.name) else set()
    for k, (mod, s) in enumerate(jobs):
        if k % nworkers != worker: continue
        key = f"{mod}:{s[0]}:{s[1]}:{s[2]}"
        if key in done: continue
        orig = open(os.path.join(cfg["repo"], mod)).read()
        new, line = apply(ast.parse(orig), s)
        if ast.dump(ast.parse(new)) == ast.dump(ast.parse(orig)): continue
        open(os.path.join(work, mod), "w").write(new)
        res = run_tests(work, cfg["tests"], cfg.get("timeout", 60))
        open(os.path.join(work, mod), "w").write(orig)
        old_line = orig.splitlines()[line - 1].strip() if line else ""
        out.write(json.dumps(dict(key=key, module=mod, kind=s[1], line=line, code=old_line, **res)) + "\n"); out.flush()
