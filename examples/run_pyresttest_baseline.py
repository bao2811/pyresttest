#!/usr/bin/env python3
"""
Wrapper to run the original pyresttest CLI from a pre-upgrade worktree in an isolated venv.

Requirements satisfied:
- does not modify pyresttest source
- does not alter YAML
- uses the original CLI by installing the package into a temp virtualenv

Usage: python examples/run_pyresttest_baseline.py --worktree ../pyresttest_preupgrade --tests examples/jsonplaceholder_tests.yaml --url https://jsonplaceholder.typicode.com

Outputs saved to outdir (default: examples/bench_results_pre_cli)
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def run(cmd, **kwargs):
    print("Run:", " ".join(cmd))
    return subprocess.run(cmd, **kwargs)


def create_venv(path):
    subprocess.check_call([sys.executable, "-m", "venv", str(path)])


def pip_install(venv_bin, pkg_path):
    pip = venv_bin / "pip"
    # upgrade pip
    run([str(pip), "install", "-U", "pip", "setuptools", "wheel"], check=True)
    run([str(pip), "install", str(pkg_path)], check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worktree", required=True, help="Path to pre-upgrade worktree containing pyresttest package")
    parser.add_argument("--tests", required=True, help="YAML file path (relative to current workspace) or absolute")
    parser.add_argument("--url", required=True, help="Base URL to pass to CLI --url")
    parser.add_argument("--outdir", default="examples/bench_results_pre_cli", help="Output directory to save results")
    parser.add_argument("--extra-args", default="", help="Extra args to forward to pyresttest CLI")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    tmpdir = Path(tempfile.mkdtemp(prefix="pyresttest_pre_env_"))
    venv_path = tmpdir / "venv"
    try:
        print("Creating temporary venv at", venv_path)
        create_venv(venv_path)
        venv_bin = venv_path / "bin"
        print("Installing pre-upgrade package from", args.worktree)
        pip_install(venv_bin, Path(args.worktree).resolve())

        cli = venv_bin / "pyresttest"
        if not cli.exists():
            raise RuntimeError("pyresttest console script not found in venv bin")

        cmd = [str(cli), "--url", args.url, "--tests", args.tests]
        if args.extra_args:
            cmd += args.extra_args.split()

        out_file = outdir / "pre_pyresttest_cli_output.txt"
        start = time.time()
        with open(out_file, "w", encoding="utf-8") as fo:
            proc = subprocess.run(cmd, stdout=fo, stderr=subprocess.STDOUT)
        end = time.time()
        wall = end - start

        summary = {
            "wall_seconds": wall,
            "returncode": proc.returncode,
            "output_file": str(out_file),
        }

        # Try to parse output for pass/fail counts
        passed = None
        failed = None
        with open(out_file, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
            # common patterns
            import re
            m = re.search(r"Passed:\s*(\d+)", text)
            if m:
                passed = int(m.group(1))
            m = re.search(r"Failed:\s*(\d+)", text)
            if m:
                failed = int(m.group(1))
            if passed is None:
                # fallback: count 'Test Succeeded' and 'Test Failed' or 'Succeeded' occurrences
                passed = len(re.findall(r"Succeeded|Test Succeeded|PASSED|Passed", text, flags=re.IGNORECASE))
                failed = len(re.findall(r"Failed|Test Failed|FAILED", text, flags=re.IGNORECASE))

        summary["parsed_passed"] = passed
        summary["parsed_failed"] = failed

        summary_file = outdir / "pre_pyresttest_cli_summary.json"
        with open(summary_file, "w", encoding="utf-8") as sf:
            json.dump(summary, sf, indent=2)

        print("Saved output to", out_file)
        print("Saved summary to", summary_file)
        print(json.dumps(summary, indent=2))

    finally:
        # cleanup venv directory to avoid leaving large temp files
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass


if __name__ == '__main__':
    main()
