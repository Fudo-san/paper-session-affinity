#!/usr/bin/env python3
"""Build the distributable source archive and refresh the artifact manifest.

Timestamps inside the archive are fixed so that two runs over the same files
produce the same bytes, and the manifest SHA-256 stays meaningful in a release.
"""
from pathlib import Path
import hashlib
import json
import zipfile

PAPER = Path(__file__).resolve().parent
ROOT = PAPER.parent
VERSION = 'v0.3'
ARCHIVE = PAPER / f'session-affinity-{VERSION}-source.zip'
MANIFEST = PAPER / f'revision/{VERSION}/artifact_manifest.json'
# The ZIP epoch. Not a claim about when anything happened; it only removes the clock.
FIXED_TIME = (1980, 1, 1, 0, 0, 0)

# What a third party needs to rebuild the PDF, plus the records the text refers to.
# Raw experiment data and the Tectonic binary stay out; see BUILD.md.
FIXED = ['main.tex', 'main.bbl', 'references.bib', 'build.sh', 'BUILD.md',
         'revision/ANALYSIS_PLAN.md', 'revision/CHANGELOG.md', 'revision/REFERENCES_REVIEW.md',
         'revision/results.json',
         f'revision/{VERSION}/ANALYSIS_PLAN.md', f'revision/{VERSION}/REFERENCES_REVIEW.md',
         f'revision/{VERSION}/RESPONSE.md', f'revision/{VERSION}/results.json']
GLOBS = ['generated/*.tex', 'figures/revision_*.pdf']


def members():
    names = list(FIXED)
    for pattern in GLOBS:
        names += [str(p.relative_to(PAPER)) for p in PAPER.glob(pattern)]
    missing = [n for n in names if not (PAPER / n).exists()]
    if missing:
        raise SystemExit(f'missing: {missing}')
    return sorted(names)


def write_archive(names):
    with zipfile.ZipFile(ARCHIVE, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in names:
            info = zipfile.ZipInfo(name, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, (PAPER / name).read_bytes())
    with zipfile.ZipFile(ARCHIVE) as z:
        bad = z.testzip()
        if bad:
            raise SystemExit(f'CRC failed: {bad}')


def refresh_manifest():
    """Re-hash exactly the paths the manifest already tracks; do not invent entries."""
    m = json.loads(MANIFEST.read_text())
    for rel in m['sha256']:
        m['sha256'][rel] = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2) + '\n')
    return m['sha256']


if __name__ == '__main__':
    names = members()
    write_archive(names)
    entries = refresh_manifest()
    digest = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    print(f'{ARCHIVE.name}: {len(names)} files, CRC ok, sha256 {digest}')
    print(f'{MANIFEST.relative_to(ROOT)}: {len(entries)} entries refreshed')
