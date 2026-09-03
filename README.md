# The Economics of Session Affinity in Multi-Agent Code Generation

**A Preregistered Study of a Commercial Coding-Agent CLI**

Does keeping related coding tasks in one continued session save money?
We preregistered the answer criteria, ran 196 paired runs, and found that **it does not**.

---

## TL;DR

Multi-agent code generation systems call an LLM once per task. Each call re-reads the
repository context from scratch. An obvious idea is to keep related tasks in the same
session so the shared history is served from cache instead of being rebuilt.

We tested that idea against a commercial coding-agent CLI under a frozen protocol.

| Hypothesis | Result | Verdict |
|---|---|---|
| **H1** Cost is reduced by ≥20% | median **+5.5%** (C is *more* expensive) | **not supported** |
| **H2** Wall-clock time is non-inferior | ratio 1.042, CI upper 1.133 < 1.15 | **supported** |
| **H3** Acceptance pass rate is non-inferior | B 100.0% / C 99.0%, CI90 lower +0.00pp | **supported** |
| **H4b** The cost model predicts the ratio | 6/7 within ±25%, but sign wrong for 2 | **not supported** |

**Lane continuation is neither slower nor lower-quality — but it is not cheaper.**

One more thing worth knowing: the effect is driven almost entirely by a single
workload shape. Excluding the *contended* specification (tasks with no dependency
but overlapping write scopes), the median difference becomes **−1.4% (p = 0.90)** —
the effect disappears. What we actually measured is the **cost of over-serialization
under contention**, not a general property of session reuse.

## Why this repository exists

Negative results are rarely published, and preregistration is rare in
empirical software engineering. This repository is the full record:
the frozen decision rules, the raw measurements, the analysis code, and
every amendment made along the way — including the mistakes.

**The preregistration is verifiable by timestamp.** `protocol/` was frozen in
commit `fefe7c4` (2026-07-31T01:55:17+09:00), before any main-experiment data existed.
Every later change is logged in `protocol/rqs_hypotheses.md` §7 as A-1 … A-6.

## What's here

| Path | Contents |
|---|---|
| `protocol/` | Preregistered decision rules (FROZEN v1.0) and the amendment log |
| `drafts/` | The paper, section by section |
| `runs/main/` | **196 runs of raw measurements** (`run.json` + `calls.jsonl`) |
| `analysis/` | E1 aggregation, E2 verdict, statistics, model predictions |
| `harness/` | Experiment driver and per-window runner |
| `benchmarks/` | Seven task specifications and their shape mapping |
| `probes/` | M1–M7 cache-behaviour probes underpinning the cost model |

The measurement data includes per-turn token usage (`num_turns`,
`peak_context_tokens`, `turns[]`) for every call — rare data for a commercial CLI.

## Reproducing the analysis (a few minutes, no API needed)

Everything needed is in this repository.

```bash
python3 analysis/e1_aggregate.py main
python3 analysis/e2_tests.py main --acknowledge-stop A-6
python3 -m pytest -q analysis/tests/       # 29 tests, synthetic data only
```

`--acknowledge-stop A-6` is required by design: E1 detects a preregistered stop
condition and refuses to produce a verdict unless a recorded resumption decision
is named. See `protocol/rqs_hypotheses.md` §7 A-6.

Secondary analyses (permitted only as secondary by `exclusion_rules` §5):

```bash
python3 analysis/sensitivity.py    # effect disappears without the contended spec
python3 analysis/pair_gaps.py      # within-pair execution intervals
python3 analysis/verify_frozen.py  # SHA-256 of the 398 frozen files
```

Re-running the **experiment** itself needs the API, the harness, and the target
repository — see `REPRODUCTION.md`. Those two repositories are **not published**,
so only the analysis is fully reproducible from this repository alone.

## Honest limitations

Read `drafts/sec8_threats.md` before drawing conclusions. The short list:

- **A central claim of ours was refuted by our own measurements.** We argued that
  cache TTL is a schedulable resource. It partly is not: the rewrite indicator ρ,
  which roughly halves the break-even point, is determined by provider-side cache
  state at init and **cannot be controlled from the client**.
- One of seven specifications determines the sign of the result.
- The infrastructure was unstable; a preregistered stop condition fired
  (see A-6 for why the run-level rate is 13.8%, not the 61.7% E1 reports).
- Single language, single target repository, single model and CLI version.
- The author is not blind: the third arm was conceived *after* seeing pilot direction
  (it was ultimately parked — see §7.5).

## License

| | |
|---|---|
| Code (`analysis/` `harness/` `benchmarks/*.py` `probes/`) | **MIT** |
| Docs and data (`drafts/` `protocol/` `runs/` `*.md` `*.csv`) | **CC BY 4.0** |

Per-file mapping is in `REUSE.toml`. Frozen artefacts carry no license headers
so their hashes stay verifiable.

**This license does not sublicense model outputs.** Provider terms — including any
restriction on competing model development — are not lifted by CC BY.
See `THIRD_PARTY_NOTICES.md`.

CC BY asks for credit on redistribution; it does **not** compel citation for the
use of plain facts such as costs or token counts. For academic citation, please
use `CITATION.cff`.

## Status

Not yet published externally. The following are pending author confirmation
(see `PUBLICATION_PLAN.md`):

- Author name, affiliation, contact
- Repository URL, Zenodo DOI, arXiv ID

---

## 日本語

商用コーディングエージェント CLI 上で、**関連タスクを同一セッションに載せると
費用が下がるか**を事前登録して検証した記録である。

**結論は「下がらない」。** 中央値で 5.5% 高く、事前登録の有意性条件と 20% 削減基準を
いずれも満たさなかった。一方で時間と品質は非劣性が成立しており、
**「遅くも粗くもならないが、安くもならない」**というのが本研究の答えである。

さらに、この効果は**単一の仕様が支配している**。競合形状（依存が無いのに
write-scope が交差する）を除くと中央値は **−1.4%（p=0.90）** となり効果が消える。
測定できたのは「セッション再利用の一般的な性質」ではなく、
**競合下での過剰直列化の代償**であった。

事前登録は commit のタイムスタンプで検証できる。`protocol/` は
`fefe7c4`（2026-07-31T01:55:17+09:00）で凍結しており、本実験のデータは
その時点で1件も存在しない。以降の変更は §7 に A-1〜A-6 として記録した。

**自分たちの中心的洞察が自分たちの測定で否定された経緯**も §7・§8 に残してある。
