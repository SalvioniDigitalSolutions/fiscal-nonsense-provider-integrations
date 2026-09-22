#!/usr/bin/env python3
"""Run all public-pricing regression suites without network requests."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
suites = ['public-rates/tests', 'public-credit', 'public-insurance', 'public-savings']
failed = False
for suite in suites:
    print(f'Running {suite}', flush=True)
    result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(root / suite), '-p', 'test_*.py', '-v'], cwd=root)
    failed = failed or result.returncode != 0
sys.exit(1 if failed else 0)
