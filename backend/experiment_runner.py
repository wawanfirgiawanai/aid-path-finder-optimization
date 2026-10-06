"""Runs the full paper experiment pipeline (experiments/run_experiments.py) as a background
process for the 'Run Paper Experiments' button, tracks its progress and serves its results.

Each run writes to experiments/runs/<run_id>/ so the published results in experiments/results/
are never overwritten. Runs use the frozen dataset and test cases, so costs are identical
to the published ones; only computation times differ between machines.
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
EXPERIMENTS = PROJECT / 'experiments'
SCRIPT = EXPERIMENTS / 'run_experiments.py'
RUNS = EXPERIMENTS / 'runs'
PUBLISHED = EXPERIMENTS / 'results'
FROZEN_PARAMS = PROJECT / 'dataset' / 'tuned_params.json'
PHASE_NAMES = {'tune': 'Hyper-parameter tuning (GA, ACO, Hybrid A*-GA)',
               'main': 'Main test cases (4 scenarios x 5 cases x 30 runs)',
               'scale': 'Scalability test cases (5-30 destinations x 5 cases x 10 runs)',
               'report': 'Statistics and figures'}
RUN_ID_RE = re.compile(r'^\d{8}-\d{6}$')
FIGURE_RE = re.compile(r'^fig_[a-z0-9_]+\.png$')


class ExperimentRunner:
    def __init__(self):
        self._lock = threading.Lock()
        self.proc = None
        self.state = 'idle'  # idle | running | done | failed | cancelled
        self.run_id = None
        self.started = None
        self.finished = None
        self.phase_idx, self.phase_total, self.phase = 0, 4, None
        self.progress_label, self.progress_done, self.progress_total = None, 0, 0
        self.log = deque(maxlen=200)
        self.returncode = None

    # ------------------------------------------------------------ control
    def start(self, jobs=None):
        with self._lock:
            if self.state == 'running':
                raise RuntimeError('An experiment run is already in progress')
            jobs = jobs or max(1, (os.cpu_count() or 2) - 2)
            self.run_id = datetime.now().strftime('%Y%m%d-%H%M%S')
            out = RUNS / self.run_id
            out.mkdir(parents=True, exist_ok=True)
            cmd = [sys.executable, '-u', '-W', 'ignore', str(SCRIPT), '--phase', 'all',
                   '--jobs', str(jobs), '--out', str(out),
                   '--params-file', str(FROZEN_PARAMS)]
            flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            self.proc = subprocess.Popen(cmd, cwd=str(PROJECT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         text=True, encoding='utf-8', errors='replace', bufsize=1,
                                         creationflags=flags)
            self.state, self.started, self.finished, self.returncode = 'running', time.time(), None, None
            self.phase_idx, self.phase, self.progress_label = 0, None, None
            self.progress_done = self.progress_total = 0
            self.log.clear()
            self.log.append(f'$ run {self.run_id} with {jobs} worker processes')
            threading.Thread(target=self._pump, daemon=True).start()
            return {'run_id': self.run_id, 'jobs': jobs}

    def cancel(self):
        with self._lock:
            if self.state != 'running' or not self.proc:
                return False
            if os.name == 'nt':  # kill the worker pool too
                subprocess.run(['taskkill', '/T', '/F', '/PID', str(self.proc.pid)], capture_output=True)
            else:
                self.proc.kill()
            self.state = 'cancelled'
            self.finished = time.time()
            self.log.append('Run cancelled by user')
            return True

    def _pump(self):
        for line in self.proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            self.log.append(line)
            m = re.match(r'\[phase\] (\d+)/(\d+) (\w+)', line)
            if m:
                self.phase_idx, self.phase_total, self.phase = int(m[1]), int(m[2]), m[3]
                self.progress_label, self.progress_done, self.progress_total = None, 0, 0
                continue
            m = re.match(r'\[progress\] (\S+) (\d+)/(\d+)', line)
            if m:
                self.progress_label, self.progress_done, self.progress_total = m[1], int(m[2]), int(m[3])
        self.returncode = self.proc.wait()
        with self._lock:
            if self.state == 'running':
                self.state = 'done' if self.returncode == 0 else 'failed'
                self.finished = time.time()

    # ------------------------------------------------------------ status
    def status(self):
        end = self.finished or time.time()
        inner = self.progress_done / self.progress_total if self.progress_total else 0.0
        overall = ((self.phase_idx - 1 + inner) / self.phase_total) if self.phase_idx else 0.0
        if self.state == 'done':
            overall = 1.0
        return {'state': self.state, 'run_id': self.run_id,
                'elapsed_s': round(end - self.started, 1) if self.started else 0,
                'phase': self.phase, 'phase_name': PHASE_NAMES.get(self.phase, self.phase),
                'phase_index': self.phase_idx, 'phase_total': self.phase_total,
                'progress_label': self.progress_label, 'progress_done': self.progress_done,
                'progress_total': self.progress_total, 'overall': round(overall, 4),
                'returncode': self.returncode, 'log': list(self.log)[-40:],
                'latest_completed': latest_completed_run()}


# ---------------------------------------------------------------- results
def latest_completed_run():
    if not RUNS.exists():
        return None
    done = sorted(p.name for p in RUNS.iterdir()
                  if RUN_ID_RE.match(p.name) and (p / 'results' / 'summary.json').exists())
    return done[-1] if done else None


def _records(path, cols=None):
    import pandas as pd
    df = pd.read_csv(path)
    if cols:
        df = df[[c for c in cols if c in df.columns]]
    return json.loads(df.to_json(orient='records'))


def load_results(run_id=None):
    run_id = run_id or latest_completed_run()
    if not run_id or not RUN_ID_RE.match(run_id):
        raise FileNotFoundError('No completed experiment run yet')
    res = RUNS / run_id / 'results'
    if not (res / 'summary.json').exists():
        raise FileNotFoundError(f'Run {run_id} has no results yet')
    import pandas as pd
    cols = ['case_id', 'group', 'algorithm', 'cost_mean', 'cost_std', 'vs_dijkstra_pct', 'optimum', 'hit_opt',
            'runs', 'time_mean_ms']
    out = {'run_id': run_id,
           'main': _records(res / 'table_main.csv'),
           'cases': _records(res / 'table_cases.csv', cols),
           'scale': _records(res / 'table_scale.csv'),
           'stats': _records(res / 'stats_cases.csv'),
           'tuned_params': json.loads((res / 'tuned_params.json').read_text()),
           'frozen_params': json.loads(FROZEN_PARAMS.read_text()) if FROZEN_PARAMS.exists() else None,
           'summary': json.loads((res / 'summary.json').read_text()),
           'figures': sorted(p.name for p in (RUNS / run_id / 'figures').glob('fig_*.png')),
           'journal_figures': sorted('journal/' + p.name for p in (RUNS / run_id / 'figures' / 'journal').glob('fig_j*.png')),
           'excel': (res / EXCEL_NAME).exists()}
    # Reproduction check: every seeded run must give the same cost and distance as the published runs
    key = ['case_id', 'algo', 'seed']
    compared, mismatches, max_diff = 0, 0, 0.0
    for fname in ('main_runs.csv', 'scale_runs.csv'):
        if not (PUBLISHED / fname).exists() or not (res / fname).exists():
            continue
        a = pd.read_csv(res / fname)[key + ['cost', 'distance']]
        b = pd.read_csv(PUBLISHED / fname)[key + ['cost', 'distance']]
        m = a.merge(b, on=key, suffixes=('', '_pub'))
        d = (m['cost'] - m['cost_pub']).abs().combine((m['distance'] - m['distance_pub']).abs(), max)
        compared += len(m)
        mismatches += int((d > 1e-6).sum())
        max_diff = max(max_diff, float(d.max()) if len(d) else 0.0)
    if compared:
        out['reproduction'] = {'compared_runs': compared, 'mismatches': mismatches, 'max_abs_diff': max_diff}
    return out


def figure_path(run_id, name):
    sub = ''
    if (name or '').startswith('journal/'):
        sub, name = 'journal', name[len('journal/'):]
    if not RUN_ID_RE.match(run_id or '') or not FIGURE_RE.match(name or ''):
        raise FileNotFoundError('Invalid figure reference')
    p = RUNS / run_id / 'figures' / sub / name
    if not p.exists():
        raise FileNotFoundError(name)
    return p


EXCEL_NAME = 'OptiRoute_Results.xlsx'


def excel_path(run_id):
    """The one-workbook export written by the report phase (experiments/export_excel.py)."""
    if not RUN_ID_RE.match(run_id or ''):
        raise FileNotFoundError('Invalid run reference')
    p = RUNS / run_id / 'results' / EXCEL_NAME
    if not p.exists():
        raise FileNotFoundError(EXCEL_NAME)
    return p
