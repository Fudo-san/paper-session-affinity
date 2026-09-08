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
TAG = 'v1.2.0-preprint'

FIXED = ['analysis/e1_dataset_main.json', 'analysis/e2_results_main.json',
         'analysis/frozen_manifest.json', 'analysis/model_predictions.json',
         'analysis/PRE_ANALYSIS_DECISIONS.md', 'run_ledger_main.csv',
         'paper/main.tex', 'paper/main.bbl', 'paper/references.bib', 'paper/main.pdf',
         'paper/main_en.tex', 'paper/main_en.bbl', 'paper/main_en.pdf',
         'paper/session-affinity-v0.3.pdf', 'paper/session-affinity-v0.3-source.zip',
         'paper/revision/results.json', 'paper/revision/v0.3/results.json',
         'paper/revision/v0.3/artifact_manifest.json',
         'CITATION.cff', 'LICENSE', 'README.md', 'REPRODUCTION.md', '.zenodo.json',
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


def check():
    """Fail if anything the manifest covers changed after it was written.

    Generating the manifest and then editing a covered document leaves a stale hash;
    that has happened twice. Run this immediately before tagging.
    """
    m = json.loads((ROOT / 'RELEASE_MANIFEST.json').read_text())
    stale = [rel for rel, want in m['sha256'].items()
             if hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != want]
    missing = sorted(set(members(tracked())) - set(m['sha256']))
    if stale or missing:
        raise SystemExit(f'stale: {stale}\nnot covered: {missing}')
    print(f"RELEASE_MANIFEST.json: {len(m['sha256'])} files match, tag {m['release_tag']}")


if __name__ == '__main__':
    import sys
    if '--check' in sys.argv:
        check()
        raise SystemExit(0)
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
