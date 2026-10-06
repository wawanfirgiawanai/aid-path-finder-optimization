"""Re-run a sample of the published runs from the frozen dataset and test cases and compare every result.

The sample covers case 01 of every group (4 main + 4 scalability cases), all six algorithms and all seeds.

  python experiments/verify_dataset.py --jobs 12
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_experiments as R  # noqa: E402

METRICS = ['cost', 'distance', 'risk_exposure', 'makespan_cost']


def main():
    import pandas as pd
    ap = argparse.ArgumentParser()
    ap.add_argument('--jobs', type=int, default=8)
    a = ap.parse_args()
    R.PARAMS_FILE = str(R.DATASET / 'tuned_params.json')
    params = R.merged_params()
    ref = pd.concat([pd.read_csv(R.RESULTS / 'main_runs.csv'), pd.read_csv(R.RESULTS / 'scale_runs.csv')])
    ref = ref[ref['case_id'].str.endswith('-01')]
    tasks = [{'phase': row.phase, 'case_id': row.case_id, 'algo': row.algo, 'params': params, 'seed': int(row.seed)}
             for row in ref.itertuples()]
    out = pd.DataFrame(R.pmap(R.run_one, tasks, a.jobs, 'verify'))
    key = ['case_id', 'algo', 'seed']
    both = out.merge(ref, on=key, suffixes=('', '_ref'))
    diff = (both[METRICS].values - both[[f'{m}_ref' for m in METRICS]].values).__abs__().max(axis=1)
    bad = both[diff > 1e-6]
    print(f'compared {len(both)} runs of {both.case_id.nunique()} test cases: {len(bad)} mismatches')
    if len(bad):
        print(bad[key + ['cost', 'cost_ref']].head(20).to_string(index=False))
        sys.exit(1)
    print('OK - the dataset and code reproduce the published results exactly')


if __name__ == '__main__':
    main()
