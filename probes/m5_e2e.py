#!/usr/bin/env python3
"""M5: 最小 E2E 実現性テスト（アームB vs アームC）.

目的: 計装を作る**前に**、中心主張の方向（C < B）が実タスクで出るかを安く確かめる。
出なければ、装置に投資する前に縮退・撤退の判断ができる。

設計:
  対象repo  : 旧agent-framework の worktree コピー（宣言済みの実験基盤・小さい＝安い）
  タスク    : fwcore/metrics.py に対する依存関係のある2件（T2 は T1 の成果物を使う）
  アームB   : 各タスクを**新規セッション**で実行（毎回 E を払う）
  アームC   : 同一セッションを **--resume で継続**（E を回避）
  実行順    : **B → C**（【A5】: resume が作ったキャッシュに fresh がヒットしうるため、
              resume を使う C を後に置く。逆順だと B が不当に安くなる）
  隔離      : アームごとに別 worktree（パスが違うのでプレフィックス一致もさらに崩れる）

計測: 呼び出しごとの実 usage / cost / session_id / wall。フレームワークは使わない
（`claude --print --output-format json` を直接呼ぶ）。

結果は m5_results.jsonl へ追記のみ。
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent / "m5_results.jsonl"
ARM_B_DIR = "/tmp/m5_armB"
ARM_C_DIR = "/tmp/m5_armC"
TOOLS = ["Read", "Edit", "Write", "Glob", "Grep"]

TASK1 = """fwcore/metrics.py に、Claude CLI の `--output-format json` 応答から実測 usage を
取り出すためのデータ構造を追加してください。

要件:
- dataclass `CallUsage` を定義する。フィールド:
  input_tokens: int, output_tokens: int, cache_read_tokens: int,
  cache_creation_tokens: int, cost_usd: float, session_id: str | None, model: str | None
- classmethod `from_cli_json(cls, data: dict) -> "CallUsage"` を追加する。
  data は CLI の JSON 応答全体（`usage` キーに input_tokens / output_tokens /
  cache_read_input_tokens / cache_creation_input_tokens、トップレベルに
  total_cost_usd / session_id / model がある想定）。欠損キーは 0 または None を入れる。
- 既存の MetricsCollector には**触らない**。追加のみ。
- 標準ライブラリのみ。"""

TASK2 = """fwcore/metrics.py の MetricsCollector に、実測 usage を集計する機能を追加してください。

要件（先に追加した CallUsage を使うこと）:
- `record_usage(self, agent_name: str, usage: CallUsage) -> None`
  エージェント名つきで内部リストへ追記する。
- `usage_totals(self) -> dict`
  記録済み CallUsage を合計し、
  {"input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens", "cost_usd"}
  を返す。記録が無ければ全て 0。
- 既存の推定値ベースの機能は**壊さない**（追加のみ）。
- 標準ライブラリのみ。"""


def find_claude() -> str | None:
    exe = shutil.which("claude")
    if exe:
        return exe
    c = Path.home() / ".local" / "bin" / "claude"
    return str(c) if c.exists() else None


def call(exe: str, prompt: str, cwd: str, label: str, arm: str,
         resume: str | None = None) -> dict:
    cmd = [exe, "--print", "--output-format", "json",
           "--allowedTools", ",".join(TOOLS)]
    if resume:
        cmd += ["--resume", resume]
    t0 = time.time()
    proc = subprocess.run(cmd, input=prompt.encode("utf-8"),
                          capture_output=True, timeout=1800, cwd=cwd)
    rec: dict = {
        "label": label, "arm": arm, "cwd": cwd, "resume": bool(resume),
        "rc": proc.returncode, "wall_s": round(time.time() - t0, 1),
        "iso": datetime.now(timezone.utc).astimezone().isoformat(),
    }
    try:
        data = json.loads(proc.stdout.decode("utf-8", errors="replace"))
        u = data.get("usage") or {}
        rec.update({
            "session_id": data.get("session_id"),
            "model": data.get("model"),
            "num_turns": data.get("num_turns"),
            "is_error": data.get("is_error"),
            "input": u.get("input_tokens"),
            "output": u.get("output_tokens"),
            "cache_w": u.get("cache_creation_input_tokens"),
            "cache_r": u.get("cache_read_input_tokens"),
            "cost_usd": data.get("total_cost_usd"),
            "result_head": str(data.get("result"))[:300],
        })
    except Exception as exc:
        rec["parse_error"] = str(exc)
        rec["stderr"] = proc.stderr.decode(errors="replace")[:600]
    with OUT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[{rec['iso'][11:19]}] {arm}/{label}: rc={rec['rc']} "
          f"turns={rec.get('num_turns')} cache_w={rec.get('cache_w')} "
          f"cache_r={rec.get('cache_r')} cost=${rec.get('cost_usd')} "
          f"wall={rec['wall_s']}s", flush=True)
    return rec


def implemented(path: str) -> dict:
    """成果物の有無（品質の粗い確認。M5 の主目的は費用だが、空実装との区別は要る）。"""
    p = Path(path) / "fwcore" / "metrics.py"
    t = p.read_text(encoding="utf-8") if p.exists() else ""
    return {"CallUsage": "class CallUsage" in t,
            "from_cli_json": "from_cli_json" in t,
            "record_usage": "def record_usage" in t,
            "usage_totals": "def usage_totals" in t,
            "lines": len(t.splitlines())}


def main() -> int:
    exe = find_claude()
    if not exe:
        print("[ERROR] claude CLI not found", file=sys.stderr)
        return 1
    print(f"claude={exe}  armB={ARM_B_DIR}  armC={ARM_C_DIR}", flush=True)

    # --- アームB: 毎回 fresh（先に実行。A5 の汚染方向を避ける） ---
    print("\n=== ARM B (fresh sessions) ===", flush=True)
    b1 = call(exe, TASK1, ARM_B_DIR, "task1", "B")
    b2 = call(exe, TASK2, ARM_B_DIR, "task2", "B")

    # --- アームC: セッション継続 ---
    print("\n=== ARM C (session continuation) ===", flush=True)
    c1 = call(exe, TASK1, ARM_C_DIR, "task1", "C")
    sid = c1.get("session_id")
    if not sid:
        print("[ABORT] arm C task1 に session_id が無い", file=sys.stderr)
        return 1
    c2 = call(exe, TASK2, ARM_C_DIR, "task2", "C", resume=sid)

    # --- 集計 ---
    def total(rs, key):
        return sum((r.get(key) or 0) for r in rs)

    B, C = [b1, b2], [c1, c2]
    summary = {
        "label": "m5_summary",
        "iso": datetime.now(timezone.utc).astimezone().isoformat(),
        "B_cost": round(total(B, "cost_usd"), 6),
        "C_cost": round(total(C, "cost_usd"), 6),
        "B_wall": round(total(B, "wall_s"), 1),
        "C_wall": round(total(C, "wall_s"), 1),
        "B_cache_w": total(B, "cache_w"), "C_cache_w": total(C, "cache_w"),
        "B_cache_r": total(B, "cache_r"), "C_cache_r": total(C, "cache_r"),
        "B_impl": implemented(ARM_B_DIR), "C_impl": implemented(ARM_C_DIR),
    }
    if summary["B_cost"]:
        summary["cost_ratio_C_over_B"] = round(summary["C_cost"] / summary["B_cost"], 4)
        summary["saving_pct"] = round(100 * (1 - summary["C_cost"] / summary["B_cost"]), 1)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(summary, ensure_ascii=False) + "\n")

    print("\n=== M5 SUMMARY ===", flush=True)
    print(f"  B (fresh)  : ${summary['B_cost']:.4f}  wall={summary['B_wall']}s "
          f"cache_w={summary['B_cache_w']:,} cache_r={summary['B_cache_r']:,}")
    print(f"  C (resume) : ${summary['C_cost']:.4f}  wall={summary['C_wall']}s "
          f"cache_w={summary['C_cache_w']:,} cache_r={summary['C_cache_r']:,}")
    if "saving_pct" in summary:
        print(f"  → C/B = {summary['cost_ratio_C_over_B']}  "
              f"削減 {summary['saving_pct']}%  "
              f"（事前基準: >=20% で『実質的削減』）")
    print(f"  実装確認 B: {summary['B_impl']}")
    print(f"  実装確認 C: {summary['C_impl']}")
    print(f"raw: {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
