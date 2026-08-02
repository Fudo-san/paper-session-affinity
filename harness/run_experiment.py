#!/usr/bin/env python3
"""A6: 実験ドライバ — spec × arm × rep を回す.

事前登録（`protocol/rqs_hypotheses.md` FROZEN v1.0）に従って実行する:

- 単位: spec × arm × rep。B と C は**同一 spec・同一反復番号で対にする**（対応付き設計）。
- アームは時間帯交互配置（ABBA）。仕様内の実行順はランダム化。
- **【A5】汚染対策（本ドライバの要）**: アームC の resume が作ったキャッシュに
  直後のアームB の fresh がヒットしうる。同一 spec の B/C は
  `--cooldown-min`（既定 12分）以上あける。M2 実測で履歴キャッシュは
  10.2分で cold になっているため、12分を既定とする。
- 除外・再実行は `protocol/exclusion_rules.md` に従い、`run_ledger.csv` に全件記録。

出力:
  runs/<spec>/<arm>/rep<k>/calls.jsonl   呼び出し単位の実測値
  runs/<spec>/<arm>/rep<k>/run.json      run 単位の要約
  run_ledger.csv                          全 run の状態台帳（追記のみ）

使い方:
  python3 harness/run_experiment.py --specs specs.json --reps 2 --dry-run
  python3 harness/run_experiment.py --specs specs.json --reps 2
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # paper-session-affinity/
FRAMEWORK = Path.home() / "project" / "旧agent-framework"
LEDGER = ROOT / "run_ledger.csv"
# 対象リポジトリの実在スプリントと衝突させないための実験専用 ID。
SPRINT_ID = "sprint_exp"


class NoModelCallError(RuntimeError):
    """モデルを1回も呼べずに run が終わった。上限・認証切れ・provider 枯渇。"""
LEDGER_FIELDS = [
    "iso", "run_id", "spec", "arm", "rep", "attempt", "status",
    "cost_usd", "wall_s", "accepted", "cli_version", "model",
    "exclusion_reason", "notes",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def cli_version() -> str:
    exe = shutil.which("claude") or "claude"
    try:
        p = subprocess.run([exe, "--version"], capture_output=True, timeout=30)
        return p.stdout.decode(errors="replace").strip()[:120]
    except Exception:
        return "unknown"


def append_ledger(row: dict) -> None:
    """run_ledger.csv へ追記（既存行は改変しない）。"""
    exists = LEDGER.exists()
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        if not exists:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in LEDGER_FIELDS})


def is_run_valid(out_dir: Path, n_tasks: int) -> bool:
    """その run が実際にモデルを呼んで**全タスク**を回しているか。

    cost=0 は空振り（上限・認証切れ）なので「済み」と見なさない。

    cost>0 だけでは足りない。4タスク中1タスクだけ実行できた run も cost>0 に
    なり、「有効な観測」として集計へ入ってしまう（2026-08-02 に m_mixed C rep3 と
    w_two_files B rep3 で発生。一方は C を、もう一方は B を不当に安く見せ、
    相対差を ±40〜85% 動かしていた）。計画したタスク数だけ呼び出しがあることを
    条件にする。

    accepted の真偽は問わない。受入に落ちること自体は正当な観測である。
    """
    rj = out_dir / "run.json"
    if not rj.exists():
        return False
    try:
        d = json.loads(rj.read_text(encoding="utf-8"))
    except Exception:
        return False
    if float((d.get("usage_actual") or {}).get("cost_usd") or 0) <= 0:
        return False
    cj = out_dir / "calls.jsonl"
    if not cj.exists():
        return False
    n_call = len([x for x in cj.read_text(encoding="utf-8").splitlines() if x.strip()])
    return n_call >= n_tasks


def load_specs(path: Path) -> list[dict]:
    """spec 定義を読む。

    1件の spec:
      {"spec_id": "...", "shape": "W|N|M|Contended|ScopeError",
       "repo": "<worktree の元 repo>", "commit": "<開始コミット>",
       "plan": "<plan.json のパス>", "verify": ["python3","-m","pytest","-q", ...]}
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    specs = data["specs"] if isinstance(data, dict) else data
    for s in specs:
        for k in ("spec_id", "repo", "commit", "plan", "verify"):
            if k not in s:
                raise ValueError(f"spec に {k} がありません: {s.get('spec_id', s)}")
    return specs


def build_schedule(specs: list[dict], reps: int, seed: int) -> list[dict]:
    """ABBA 交互配置 ＋ 仕様内ランダム化（protocol §5）。

    同一 spec の同一 rep で B と C を対にし、その順序を反復ごとに反転させる
    （ABBA）。仕様の実行順は seed 固定でランダム化する。

    **アーム主体で並べる**（2026-08-02 変更）。以前は spec 主体で B と C を隣接させて
    いたため、A5 汚染回避の cooldown が毎回まるごと sleep になっていた。
    1 rep 内で「全仕様の第1アーム → 全仕様の第2アーム」の順に流せば、ある仕様の
    B と C の間に他仕様の実行が挟まり、待ち時間が実作業で埋まる。
    cooldown 判定は経過時間で見ているので、自然な間隔が足りていれば sleep しない。

    アームと時間帯の交絡は rep ごとのアーム順反転（ABBA）が担う。
    """
    rng = random.Random(seed)
    units: list[dict] = []
    for rep in range(1, reps + 1):
        order = list(specs)
        rng.shuffle(order)
        arms = ("B", "C") if rep % 2 == 1 else ("C", "B")
        for arm in arms:
            for spec in order:
                units.append({"spec": spec, "arm": arm, "rep": rep})
    return units


def prepare_worktree(spec: dict, arm: str, rep: int, workdir: Path) -> Path:
    """アーム×反復ごとに隔離した worktree を用意する（相互汚染の防止）。"""
    wt = workdir / f"{spec['spec_id']}_{arm}_rep{rep}"
    if wt.exists():
        subprocess.run(["git", "-C", spec["repo"], "worktree", "remove", "--force", str(wt)],
                       capture_output=True)
    subprocess.run(["git", "-C", spec["repo"], "worktree", "add", "-f",
                    str(wt), spec["commit"]], check=True, capture_output=True)
    return wt


def run_verify(wt: Path, verify: list[str]) -> tuple[bool, str]:
    """受入判定。protocol §2 の『受入全通過率』は spec×rep ごとの二値。"""
    try:
        p = subprocess.run(verify, cwd=str(wt), capture_output=True, timeout=1800)
    except subprocess.TimeoutExpired:
        return False, "verify timeout"
    tail = p.stdout.decode(errors="replace")[-400:]
    return p.returncode == 0, tail


def main() -> int:
    ap = argparse.ArgumentParser(description="paper experiment driver (spec x arm x rep)")
    ap.add_argument("--specs", required=True, help="spec 定義 JSON")
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--seed", type=int, default=20260801, help="実行順ランダム化の種（記録する）")
    ap.add_argument("--cooldown-min", type=float, default=12.0,
                    help="同一 spec の B/C 間に空ける分数（A5 汚染対策。M2 実測 10.2分 cold に基づく）")
    ap.add_argument("--workdir", default="/tmp/paper_runs")
    ap.add_argument("--dry-run", action="store_true",
                    help="スケジュールと隔離だけ行い、モデルを呼ばない")
    ap.add_argument("--skip-done", action="store_true",
                    help="有効な結果（cost>0）が既にある run を飛ばして再開する")
    ap.add_argument("--label", default="",
                    help="実行フェーズ名（smoke/pilot/main）。出力先と台帳を分ける。"
                         "既存フェーズの結果を上書きしないために必ず指定する")
    args = ap.parse_args()

    # 台帳はフェーズごとに分ける。1本の CSV に列を足すと、既存ヘッダと
    # 追記行の列数がずれて過去のデータが壊れるため。
    global LEDGER
    if args.label:
        LEDGER = ROOT / f"run_ledger_{args.label}.csv"

    specs = load_specs(Path(args.specs))
    schedule = build_schedule(specs, args.reps, args.seed)
    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    ver = cli_version()

    print(f"specs={len(specs)} reps={args.reps} units={len(schedule)} "
          f"seed={args.seed} cooldown={args.cooldown_min}min cli={ver}")
    if args.dry_run:
        print("\n=== 実行順（dry-run） ===")
        for i, u in enumerate(schedule, 1):
            print(f"  {i:>3}. {u['spec']['spec_id']:<16} arm={u['arm']} rep={u['rep']}")

    last_run_at: dict[tuple[str, int], float] = {}   # (spec_id, rep) -> 直前 run の終了時刻
    for i, unit in enumerate(schedule, 1):
        spec, arm, rep = unit["spec"], unit["arm"], unit["rep"]
        run_id = f"{spec['spec_id']}_{arm}_rep{rep}"
        key = (spec["spec_id"], rep)

        base = ROOT / "runs" / args.label if args.label else ROOT / "runs"
        out_dir = base / spec["spec_id"] / arm / f"rep{rep}"

        # --- 再開 -----------------------------------------------------------
        # 上限は今後も来る。当たるたびに全部やり直すのは費用が持たない。
        # 有効な結果（cost>0）が既にある run は飛ばす。cost=0 の run は
        # 空振りなので残さず、やり直す。
        #
        # **cooldown より前に判定する**。順序を逆にすると、既に終わっている run の
        # ために12分眠ってから飛ばすことになる（2026-08-02 に実際に発生）。
        # また、スキップした run で last_run_at を更新してはならない。
        # 実際にモデルを叩いたのは過去の別プロセスであり、「たった今走った」
        # 扱いにすると対アームへ不要な待機を課す。
        n_tasks = len(json.loads(
            Path(spec["plan"]).read_text(encoding="utf-8"))["tasks"])
        if args.skip_done and is_run_valid(out_dir, n_tasks):
            print(f"[{i}/{len(schedule)}] {run_id}  [SKIP] 有効な結果あり")
            continue

        # --- A5 汚染対策: 同一 spec/rep の対アームからクールダウンを空ける ---
        prev = last_run_at.get(key)
        if prev is not None:
            wait = args.cooldown_min * 60 - (time.time() - prev)
            if wait > 0:
                print(f"  [COOLDOWN] {run_id}: {wait/60:.1f}分待機（A5 汚染回避）")
                if not args.dry_run:
                    time.sleep(wait)

        out_dir.mkdir(parents=True, exist_ok=True)
        wt = prepare_worktree(spec, arm, rep, workdir)
        print(f"[{i}/{len(schedule)}] {run_id}  worktree={wt}")

        if args.dry_run:
            append_ledger({"iso": now_iso(), "run_id": run_id, "spec": spec["spec_id"],
                           "arm": arm, "rep": rep, "attempt": 1, "status": "dry_run",
                           "cli_version": ver, "notes": "dry-run（モデル未呼び出し）"})
            last_run_at[key] = time.time()
            continue

        t0 = time.time()
        status, cost, accepted, note = "failed", "", "", ""
        try:
            sys.path.insert(0, str(FRAMEWORK))
            import asyncio

            from fwcore.calls_log import CallsLogger      # noqa: E402
            from fwcore.sprint import SprintOrchestrator  # noqa: E402

            # 実験専用の sprint id を使う。対象リポジトリには実在の sprint_1 が
            # あり、その sprints/sprint_1/ には sprint_done.json と過去の results/
            # が入っている。sprint_done.json は fwcore/sprint.py の
            # is_sprint_done() で SKIP を引き起こすため、衝突させてはならない。
            # 毎回まっさらから始めるためにディレクトリごと作り直す。
            sprint_dir = wt / "sprints" / SPRINT_ID
            if sprint_dir.exists():
                shutil.rmtree(sprint_dir)
            sprint_dir.mkdir(parents=True, exist_ok=True)
            (sprint_dir / "plan.json").write_text(
                Path(spec["plan"]).read_text(encoding="utf-8"), encoding="utf-8")

            orch = SprintOrchestrator(
                wt, framework_root=FRAMEWORK,
                session_mode=("lane" if arm == "C" else "fresh"),
            )
            # --- provider フォールバックの遮断（2026-08-02）--------------------
            # ProviderScheduler は primary が落ちると既定で codex へ落ちる
            # （mk2_config providers.fallback の既定値が "codex"）。
            # 実験でこれが起きると、
            #   - CodexCliBackend.supports_resume = False なので
            #     **アームCが黙ってアームB相当に成り下がる**
            #   - モデルが変わるのでコストが比較不能になる
            # いずれも記録上は「成功した run」に見えてしまう。
            # 実験中は落とさず、落ちたら空振りとして中断させる。
            orch.runner.provider_scheduler.fallback = None

            orch.runner.calls_logger = CallsLogger(
                out_dir / "calls.jsonl", spec=spec["spec_id"], arm=arm, rep=rep)
            # run ごとに一意。run をまたぐ prefix cache 共有を遮断する（A5）。
            orch.runner.run_nonce = f"{run_id}-{uuid.uuid4().hex[:12]}"

            # plan.json → SprintPlan は ArtifactStore.load_plan が正本
            # （SprintPlan.from_dict は存在しない。2026-08-01 実確認）
            plan = orch.store.load_plan(SPRINT_ID)

            asyncio.run(orch.development_phase(SPRINT_ID, plan))
            totals = orch.runner.metrics.usage_totals()
            cost = totals.get("cost_usd", 0.0)

            # --- 空振り検知 ---------------------------------------------------
            # 2026-08-02: 利用上限に当たった際、backend がすぐ失敗を返し、
            # development_phase は例外を出さずに戻る。その結果 cost=0・
            # トークン0・wall 3秒の run が `completed` として記録され、
            # ドライバは残り25本を空回しし、何もしないまま 12分の cooldown を
            # 2回眠った。モデルを1回も呼べていない run は即座に打ち切る。
            n_logged = 0
            _cj = out_dir / "calls.jsonl"
            if _cj.exists():
                n_logged = len([x for x in _cj.read_text(encoding="utf-8").splitlines()
                                if x.strip()])
            if cost and n_logged < n_tasks:
                raise NoModelCallError(
                    f"部分実行: {n_logged}/{n_tasks} タスクしかモデルを呼べなかった。"
                    f"観測として扱ってはならない")
            if not cost:
                raise NoModelCallError(
                    f"モデル呼び出しが記録されなかった（cost=0, "
                    f"tokens={totals.get('cache_read_tokens', 0)}）。"
                    f"利用上限・認証切れ・provider 枯渇の可能性がある")
            ok, tail = run_verify(wt, spec["verify"])
            accepted = "1" if ok else "0"
            status = "completed"
            note = tail[-200:].replace("\n", " ")
            (out_dir / "run.json").write_text(json.dumps({
                "run_id": run_id, "spec": spec["spec_id"], "arm": arm, "rep": rep,
                "iso": now_iso(), "cli_version": ver, "seed": args.seed,
                "usage_actual": totals, "accepted": ok, "verify_tail": tail,
                "wall_s": round(time.time() - t0, 1),
            }, ensure_ascii=False, indent=2), encoding="utf-8")
        except NoModelCallError as exc:
            note = f"NoModelCallError: {exc}"[:300]
            append_ledger({
                "iso": now_iso(), "run_id": run_id, "spec": spec["spec_id"], "arm": arm,
                "rep": rep, "attempt": 1, "status": "aborted", "cost_usd": 0,
                "wall_s": round(time.time() - t0, 1), "accepted": "",
                "cli_version": ver, "notes": note,
            })
            print(f"\n[ABORT] {run_id}: {note}", file=sys.stderr)
            print("  空振りを検出したので中断する。原因を解消してから、"
                  "同じコマンドに --skip-done を付けて再開すること。", file=sys.stderr)
            print(f"\n台帳: {LEDGER}")
            return 2
        except Exception as exc:
            status, note = "error", f"{type(exc).__name__}: {exc}"[:300]
            print(f"  [ERROR] {run_id}: {note}", file=sys.stderr)

        append_ledger({
            "iso": now_iso(), "run_id": run_id, "spec": spec["spec_id"], "arm": arm,
            "rep": rep, "attempt": 1, "status": status, "cost_usd": cost,
            "wall_s": round(time.time() - t0, 1), "accepted": accepted,
            "cli_version": ver, "notes": note,
        })
        last_run_at[key] = time.time()
        print(f"  -> {status} cost={cost} accepted={accepted} "
              f"wall={time.time()-t0:.0f}s")

    print(f"\n台帳: {LEDGER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
