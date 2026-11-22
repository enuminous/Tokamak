"""Run the bounded OPENSTEP-005 suite and return nonzero on assertion failure."""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
COMMANDS = [('preflight.py',), ('contour.py','controls'), ('contour.py','physical'),
            ('derivative_cache.py',), ('footprints.py',), ('wall_feedback.py',), ('report.py',)]

for command in COMMANDS:
    print('Running', ' '.join(command), flush=True)
    if command[0]=='report.py':
        subprocess.run([sys.executable, *command], cwd=ROOT, check=True)
    else:
        (ROOT/'logs').mkdir(exist_ok=True)
        label=command[0].removesuffix('.py')+('-'+command[1] if len(command)>1 else '')
        with (ROOT/'logs'/(label+'.log')).open('w') as log:
            subprocess.run([sys.executable, *command], cwd=ROOT, check=True, stdout=log, stderr=subprocess.STDOUT)
summary = json.loads((ROOT/'results/summary.json').read_text())
raise SystemExit(1 if summary['failed'] else 0)
