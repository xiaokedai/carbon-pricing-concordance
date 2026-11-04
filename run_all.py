#!/usr/bin/env python3
"""Run the whole pipeline from scratch, in order.

    pip install -r requirements.txt
    python3 run_all.py              # every step; needs the ECP file (see data/README.md)
    python3 run_all.py --skip-ecp   # only the steps that need no downloaded data

Each step is the same command as in the README, run as its own process from the
repository root. Every step prints a start line and an end line. The run stops at the
first step that fails, says which step it was, and exits with status 1. A step that
exits cleanly but does not write all of its expected output files also counts as
failed.

The pipeline uses no random numbers, so there is no seed to fix.
"""
import argparse
import os
import shlex
import subprocess
import sys
import time
from importlib import metadata

import config
from config import rel

YEAR = 2019                  # year of Tables 4-6 and Figure 1 (the README headline numbers)
EXAMPLE_REGION = "Germany"   # jurisdiction of the worked examples in Table 6
TESTED_PYTHON = (3, 12)      # requirements.txt was verified on this Python version
REQUIREMENTS = config.repo_path("requirements.txt")


class Step:
    def __init__(self, name, what, args, outputs=(), needs_ecp=False):
        self.name = name
        self.what = what
        self.args = args            # command line after `python`
        self.outputs = list(outputs)
        self.needs_ecp = needs_ecp  # skipped under --skip-ecp


def build_steps(skip_ecp):
    ecp = rel(config.ECP_INDUSTRY)

    def src(script):
        return rel(config.SRC_DIR / script)

    return [
        Step("verify_crosswalk",
             "integrity checks on the crosswalk tables"
             + (" (check 4 skipped: it needs the ECP file)" if skip_ecp else ""),
             [src("verify_crosswalk.py")] + ([] if skip_ecp else ["--ecp", ecp])),
        Step("make_strict_crosswalk",
             "rebuild the strict SIC -> GLORIA mapping and check it against the distributed file",
             [src("make_strict_crosswalk.py"), "--check"]),
        Step("concordance_stats",
             "Tables 1-3 and the headline numbers",
             [src("concordance_stats.py")],
             outputs=[config.TABLE1, config.TABLE2, config.TABLE3, config.STATS_SUMMARY]),
        Step("price_dispersion",
             f"Tables 4-6 and Figure 1 ({YEAR})",
             [src("price_dispersion.py"), "--ecp", ecp, "--year", str(YEAR),
              "--example-region", EXAMPLE_REGION],
             outputs=[config.table4_path(YEAR), config.table5_path(YEAR),
                      config.table6_path(YEAR), config.figure1_path(YEAR)],
             needs_ecp=True),
        Step("merge_firms_to_ecp",
             "attach carbon prices to the demo firm panel",
             [src("merge_firms_to_ecp.py"), rel(config.DEMO_FIRMS), "--ecp", ecp],
             outputs=[config.FIRMS_WITH_ECP],
             needs_ecp=True),
    ]


def preflight(skip_ecp):
    """Check Python, package versions and input files. Returns a list of fatal problems."""
    print(f"    Python {sys.version.split()[0]}")
    if sys.version_info[:2] != TESTED_PYTHON:
        print(f"    WARNING: the pinned requirements were verified on Python "
              f"{'.'.join(map(str, TESTED_PYTHON))}; results may differ on this version.")

    mismatched = []
    if REQUIREMENTS.exists():
        for line in REQUIREMENTS.read_text().splitlines():
            line = line.split("#")[0].strip()
            if not line or ";" in line:      # skip blanks and platform-specific pins
                continue
            name, pinned = line.split("==")
            try:
                installed = metadata.version(name)
            except metadata.PackageNotFoundError:
                installed = "not installed"
            if installed != pinned:
                mismatched.append(f"{name} {installed} (requirements.txt: {pinned})")
    if mismatched:
        print("    WARNING: installed packages differ from requirements.txt; results may differ:")
        for m in mismatched:
            print(f"      - {m}")
        print("      fix with: pip install -r requirements.txt")
    else:
        print("    packages match requirements.txt")

    problems = []
    inputs = [config.MASTER, config.STRICT, config.STRICT_OVERRIDES, config.REGION_TO_FIC,
              config.DEMO_FIRMS]
    for p in inputs:
        if not p.exists():
            problems.append(f"missing input file {rel(p)} (it is part of the repository; "
                            f"restore it with `git checkout -- {rel(p)}`)")
    if not skip_ecp and not config.ECP_INDUSTRY.exists():
        problems.append(f"missing raw data file {rel(config.ECP_INDUSTRY)}. Download it as described "
                        f"in data/README.md, or run `python3 run_all.py --skip-ecp` to run only "
                        f"the steps that need no downloaded data.")
    if not problems:
        print("    input files present")
    return problems


def run_step(step, env):
    """Run one step. Returns None on success, otherwise a description of the failure."""
    t0 = time.time()
    proc = subprocess.run([sys.executable] + step.args, cwd=config.ROOT, env=env)
    if proc.returncode != 0:
        return f"exited with code {proc.returncode}"
    stale = [p for p in step.outputs if not p.exists() or p.stat().st_mtime < t0 - 2]
    if stale:
        return "exited normally but did not write " + ", ".join(rel(p) for p in stale)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--skip-ecp", action="store_true",
                    help="skip the steps that need the downloaded ECP file (see data/README.md)")
    a = ap.parse_args()

    steps = build_steps(a.skip_ecp)
    n = len(steps)
    env = dict(os.environ, PYTHONUNBUFFERED="1")   # keep each step's output in order
    t_all = time.time()

    print("==> [preflight] Python, packages and input files", flush=True)
    problems = preflight(a.skip_ecp)
    if problems:
        print("!!! [preflight] FAILED", file=sys.stderr)
        for p in problems:
            print(f"    - {p}", file=sys.stderr)
        print(f"\nPipeline stopped before step 1/{n}: no step was run.", file=sys.stderr)
        sys.exit(1)
    print("<== [preflight] done", flush=True)

    done, skipped = [], []
    for i, step in enumerate(steps, 1):
        label = f"[{i}/{n}] {step.name}"
        if a.skip_ecp and step.needs_ecp:
            print(f"\n--- {label}: SKIPPED (--skip-ecp; this step needs {rel(config.ECP_INDUSTRY)})",
                  flush=True)
            skipped.append(step.name)
            continue
        cmd = "python3 " + shlex.join(step.args)
        print(f"\n==> {label}: {step.what}\n    $ {cmd}", flush=True)
        t0 = time.time()
        error = run_step(step, env)
        dt = time.time() - t0
        if error:
            print(f"!!! {label} FAILED after {dt:.1f}s: {error}", file=sys.stderr)
            print(f"    command: {cmd}", file=sys.stderr)
            print("    The step's own error output, if any, is printed above.", file=sys.stderr)
            print(f"\nPipeline stopped at step {i}/{n} ({step.name}).", file=sys.stderr)
            print(f"  completed: {', '.join(done) or '(none)'}", file=sys.stderr)
            rest = [s.name for s in steps[i:]]
            print(f"  not run:   {', '.join(rest) or '(none)'}", file=sys.stderr)
            sys.exit(1)
        print(f"<== {label}: done in {dt:.1f}s", flush=True)
        done.append(step.name)

    print(f"\nAll {len(done)} steps finished in {time.time() - t_all:.1f}s"
          + (f"; skipped: {', '.join(skipped)}" if skipped else "") + ".")
    written = [p for s in steps if s.name in done for p in s.outputs]
    if written:
        print("Outputs written:")
        for p in written:
            print(f"  {rel(p)}")


if __name__ == "__main__":
    main()
