#!/usr/bin/env python3
"""Hash everything a release claims to contain, so a copy can be checked against it.

PUBLICATION_PLAN.md §7 fixes the scope: the frozen protocol, the E1/E2 outputs, the
run ledger, every raw run record, and the paper source with its PDF. The commit SHA is
not written here — a file cannot hash the commit that contains it. The annotated tag
carries this file's SHA-256 instead, so the chain runs tag -> commit -> this file -> data.
"""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parent
TAG = 'v1.1.0-preprint'

FIXED = ['analysis/e1_dataset_main.json', 'analysis/e2_results_main.json',
         'analysis/frozen_manifest.json', 'analysis/model_predictions.json',
         'analysis/PRE_ANALYSIS_DECISIONS.md', 'run_ledger_main.csv',
         'paper/main.tex', 'paper/main.bbl', 'paper/references.bib', 'paper/main.pdf',
         'paper/main_en.tex', 'paper/main_en.bbl', 'paper/main_en.pdf',
         'paper/session-affinity-v0.3.pdf', 'paper/session-affinity-v0.3-source.zip',
         'paper/revision/results.json', 'paper/revision/v0.3/results.json',
         'paper/revision/v0.3/artifact_manifest.json',
         'CITATION.cff', 'LICENSE', 'README.md', 'REPRODUCTION.md',
         'PUBLICATION_PLAN.md', 'THIRD_PARTY_NOTICES.md']
GLOBS = ['protocol/*.md', 'paper/generated/*.tex', 'paper/generated/en/*.tex', 'paper/figures/revision_*.pdf',
         'runs/main/**/run.json', 'runs/main/**/calls.jsonl']


def tracked():
    """Only files git actually carries; an untracked stray must not enter a release."""
    out = subprocess.run(['git', '-C', str(ROOT), 'ls-files'], capture_output=True, text=True, check=True)
    return set(out.stdout.split('\n')) - {''}


def members(known):
    names = [n for n in FIXED]
    for pattern in GLOBS:
        names += [str(p.relative_to(ROOT)) for p in ROOT.glob(pattern)]
    missing = [n for n in names if n not in known]
    if missing:
        raise SystemExit(f'not tracked by git: {missing}')
    return sorted(set(names))


if __name__ == '__main__':
    names = members(tracked())
    entries = {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in names}
    groups = {'protocol': 'protocol/', 'run_records': 'runs/main/', 'paper': 'paper/'}
    manifest = {'release_tag': TAG,
                'commit': 'recorded in the annotated tag, not here',
                'file_count': len(entries),
                'counts': {k: sum(n.startswith(v) for n in names) for k, v in groups.items()},
                'sha256': entries}
    path = ROOT / 'RELEASE_MANIFEST.json'
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(f'{path.name}: {len(entries)} files')
    for k, v in manifest['counts'].items():
        print(f'  {k}: {v}')
    print(f'sha256 {hashlib.sha256(path.read_bytes()).hexdigest()}')
