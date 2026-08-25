"""E1/E2 を**合成データ**で検証する.

実験データで挙動を確かめると、分析手法を結果に合わせて調整でき、
結果を先に覗くことにもなる（`pre_pilot_decisions.md` 決定4、stats.py の方針と同じ）。
ここでは「規則どおりに動くか」だけを、答えが分かっている人工データで確かめる。
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEDGER_COLS = ["iso", "run_id", "spec", "arm", "rep", "attempt", "status",
               "cost_usd", "wall_s", "accepted", "cli_version", "model",
               "exclusion_reason", "notes"]


def _write_fixture(tmp: Path, label: str, pairs, *, status_override=None,
                   cli_by_run=None, model_by_run=None):
    """台帳と calls.jsonl の最小構成を作る。"""
    runs_root = tmp / "runs" / label
    rows = []
    for spec, rep, cb, cc, wb, wc, ab, ac in pairs:
        for arm, cost, wall, acc in (("B", cb, wb, ab), ("C", cc, wc, ac)):
            rid = f"{spec}_{arm}_rep{rep}"
            status = (status_override or {}).get(rid, "completed")
            rows.append({
                "iso": "2026-08-25T00:00:00+09:00", "run_id": rid, "spec": spec,
                "arm": arm, "rep": rep, "attempt": 1, "status": status,
                "cost_usd": cost, "wall_s": wall, "accepted": acc,
                "cli_version": (cli_by_run or {}).get(rid, "2.1.220"),
                "model": "", "exclusion_reason": "",
                "notes": "" if status == "completed" else "NoModelCallError: provider 枯渇",
            })
            d = runs_root / spec / arm / f"rep{rep}"
            d.mkdir(parents=True, exist_ok=True)
            (d / "calls.jsonl").write_text(json.dumps({
                "spec": spec, "arm": arm, "rep": rep, "task_id": "T-1",
                "cost_usd": cost, "resumed": arm == "C",
                "model": (model_by_run or {}).get(rid, "claude-sonnet-5"),
                "cli_version": (cli_by_run or {}).get(rid, "2.1.220"),
            }, ensure_ascii=False) + "\n", encoding="utf-8")

    led = tmp / f"run_ledger_{label}.csv"
    with led.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_COLS)
        w.writeheader()
        w.writerows(rows)
    return runs_root


def _run(script: str, label: str, cwd: Path) -> subprocess.CompletedProcess:
    # **砂場側のコピー**を実行する。スクリプトは __file__ から ROOT を導くため、
    # 実体を実行すると本物の analysis/ を読み書きしてしまう。
    return subprocess.run(
        [sys.executable, str(cwd / "analysis" / script), label],
        cwd=str(cwd), capture_output=True, text=True)


def _prepare_sandbox(tmp_path: Path) -> Path:
    """analysis/ を参照できる砂場を作る（スクリプトは ROOT 相対で書く）。"""
    sandbox = tmp_path / "sandbox"
    (sandbox / "analysis").mkdir(parents=True)
    for name in ("stats.py", "e1_aggregate.py", "e2_tests.py"):
        (sandbox / "analysis" / name).write_text(
            (ROOT / "analysis" / name).read_text(encoding="utf-8"), encoding="utf-8")
    return sandbox


class TestE1:
    def test_all_completed_pairs_are_kept(self, tmp_path):
        sb = _prepare_sandbox(tmp_path)
        _write_fixture(sb, "syn", [("s1", 1, 1.0, 1.2, 10, 12, 1, 1),
                                   ("s2", 1, 2.0, 1.8, 20, 22, 1, 1)])
        p = _run("e1_aggregate.py", "syn", sb)
        assert p.returncode == 0, p.stderr
        ds = json.loads((sb / "analysis" / "e1_dataset_syn.json").read_text(encoding="utf-8"))
        assert ds["n_pairs"] == 2
        assert ds["stop_conditions"] == []

    def test_incomplete_arm_drops_the_whole_pair(self, tmp_path):
        """片アームが無効ならペアごと落とす（exclusion_rules §3）。"""
        sb = _prepare_sandbox(tmp_path)
        _write_fixture(sb, "syn", [("s1", 1, 1.0, 1.2, 10, 12, 1, 1),
                                   ("s2", 1, 2.0, 1.8, 20, 22, 1, 1)],
                       status_override={"s2_C_rep1": "aborted"})
        _run("e1_aggregate.py", "syn", sb)
        ds = json.loads((sb / "analysis" / "e1_dataset_syn.json").read_text(encoding="utf-8"))
        assert ds["n_pairs"] == 1
        assert ds["dropped_pairs"][0]["spec"] == "s2"

    def test_multiple_cli_versions_trigger_stop(self, tmp_path):
        """CLI が2種類あれば混ぜて集計せず停止（§4）。"""
        sb = _prepare_sandbox(tmp_path)
        _write_fixture(sb, "syn", [("s1", 1, 1.0, 1.2, 10, 12, 1, 1),
                                   ("s2", 1, 2.0, 1.8, 20, 22, 1, 1)],
                       cli_by_run={"s2_C_rep1": "2.1.999"})
        _run("e1_aggregate.py", "syn", sb)
        ds = json.loads((sb / "analysis" / "e1_dataset_syn.json").read_text(encoding="utf-8"))
        assert any("CLI" in s for s in ds["stop_conditions"])

    def test_high_infra_failure_ratio_triggers_stop(self, tmp_path):
        """インフラ起因の再実行率が 20% を超えたら停止（§3）。"""
        sb = _prepare_sandbox(tmp_path)
        _write_fixture(sb, "syn",
                       [("s1", 1, 1.0, 1.2, 10, 12, 1, 1),
                        ("s2", 1, 2.0, 1.8, 20, 22, 1, 1)],
                       status_override={"s1_B_rep1": "aborted", "s2_B_rep1": "aborted"})
        _run("e1_aggregate.py", "syn", sb)
        ds = json.loads((sb / "analysis" / "e1_dataset_syn.json").read_text(encoding="utf-8"))
        assert ds["rerun_ratio"] > 0.20
        assert any("再実行率" in s for s in ds["stop_conditions"])


class TestE2:
    @staticmethod
    def _pairs_with_reduction(frac: float, n: int = 12):
        """C が B より frac だけ安い合成データ（品質・時間は同等）。"""
        out = []
        for i in range(n):
            b = 1.0 + 0.01 * i
            out.append((f"s{i}", 1, b, b * (1 - frac), 10.0, 10.0, 1, 1))
        return out

    def test_clear_reduction_supports_central_claim(self, tmp_path):
        sb = _prepare_sandbox(tmp_path)
        _write_fixture(sb, "syn", self._pairs_with_reduction(0.30))
        _run("e1_aggregate.py", "syn", sb)
        p = _run("e2_tests.py", "syn", sb)
        assert p.returncode == 0, p.stderr
        res = json.loads((sb / "analysis" / "e2_results_syn.json").read_text(encoding="utf-8"))
        assert res["H1_cost"]["significant"] is True
        assert res["H1_cost"]["substantial_reduction"] is True
        assert res["H2_time"]["non_inferior"] is True
        assert res["H3_quality"]["non_inferior"] is True
        assert res["central_claim_supported"] is True

    def test_small_reduction_is_reported_as_not_substantial(self, tmp_path):
        """有意でも 20% 未満なら中心主張は掲げられない（§3 H1）。"""
        sb = _prepare_sandbox(tmp_path)
        _write_fixture(sb, "syn", self._pairs_with_reduction(0.05))
        _run("e1_aggregate.py", "syn", sb)
        _run("e2_tests.py", "syn", sb)
        res = json.loads((sb / "analysis" / "e2_results_syn.json").read_text(encoding="utf-8"))
        assert res["H1_cost"]["substantial_reduction"] is False
        assert res["central_claim_supported"] is False

    def test_cost_increase_is_reported_as_such(self, tmp_path):
        """C が高い場合、削減としては扱わない（スピンしない）。"""
        sb = _prepare_sandbox(tmp_path)
        _write_fixture(sb, "syn", self._pairs_with_reduction(-0.25))
        _run("e1_aggregate.py", "syn", sb)
        _run("e2_tests.py", "syn", sb)
        res = json.loads((sb / "analysis" / "e2_results_syn.json").read_text(encoding="utf-8"))
        assert res["H1_cost"]["direction"] == "C_more_expensive"
        assert res["H1_cost"]["substantial_reduction"] is False
        assert res["central_claim_supported"] is False

    def test_time_regression_blocks_the_central_claim(self, tmp_path):
        """費用が下がっても時間が 15% を超えて悪化すればゲートで止まる（§4）。"""
        sb = _prepare_sandbox(tmp_path)
        pairs = [(f"s{i}", 1, 1.0 + 0.01 * i, (1.0 + 0.01 * i) * 0.7, 10.0, 20.0, 1, 1)
                 for i in range(12)]
        _write_fixture(sb, "syn", pairs)
        _run("e1_aggregate.py", "syn", sb)
        _run("e2_tests.py", "syn", sb)
        res = json.loads((sb / "analysis" / "e2_results_syn.json").read_text(encoding="utf-8"))
        assert res["H1_cost"]["substantial_reduction"] is True
        assert res["H2_time"]["non_inferior"] is False
        assert res["central_claim_supported"] is False

    def test_missing_predictions_makes_h4b_undecidable(self, tmp_path):
        """予測ファイルが無ければ黙って飛ばさず「判定不能」と出す（R1 の要件）。"""
        sb = _prepare_sandbox(tmp_path)
        _write_fixture(sb, "syn", self._pairs_with_reduction(0.30))
        _run("e1_aggregate.py", "syn", sb)
        _run("e2_tests.py", "syn", sb)
        res = json.loads((sb / "analysis" / "e2_results_syn.json").read_text(encoding="utf-8"))
        assert res["H4b_model"]["verdict"] is None
        assert "判定不能" in res["H4b_model"]["note"]

    def test_stop_condition_blocks_judgment(self, tmp_path):
        """E1 が停止条件を出したら E2 は判定を出さない。"""
        sb = _prepare_sandbox(tmp_path)
        _write_fixture(sb, "syn", self._pairs_with_reduction(0.30),
                       cli_by_run={"s0_C_rep1": "2.1.999"})
        _run("e1_aggregate.py", "syn", sb)
        p = _run("e2_tests.py", "syn", sb)
        assert p.returncode == 2
        assert "停止条件" in p.stdout
