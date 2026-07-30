#!/usr/bin/env python3
"""resume プローブ: 仮定【A3】の検証 / TTL 実効生存の測定.

検証内容: claude CLI の --resume で継承した履歴 H がキャッシュ可能プレフィックスとして
扱われるか、およびその生存時間。

**設計上の要点（2026-07-31 改修）**: resume は成功した時点でキャッシュ寿命を延長する。
そのため単一セッションでギャップを伸ばしながら連続測定すると cold 境界を過大評価する。
本スクリプトは **1測定 = 1新規セッション** を厳守する。

モード:
  warm    : 新規セッション → 即 resume            → cache_read ≈ H を予測（1/12.7 の再現）
  gap     : 新規セッション → g 分待機 → resume    → TTL 実効生存の探索
  switch  : 新規セッション → 即 resume(別モデル)  → キャッシュ全損を予測
  xsession: 同一プレフィックスで新規セッションを2本  → クロスセッション prefix cache の有無(M4)
  legacy  : 旧来の単一セッション連続測定（再現用。新規測定には使わない）

計画と判定規則: probes/PROBE_PLAN.md / protocol/rqs_hypotheses.md H4(a)
結果は resume_probe_results.jsonl へ **追記のみ**（改変禁止）。
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent / "resume_probe_results.jsonl"
PREFIX_LINES = 500  # 約30,000 chars。最小キャッシュ単位を確実に超える
WARM_RATIO = 0.9    # 分類閾値（PROBE_PLAN §2 で測定前に固定）


def find_claude() -> str | None:
    exe = shutil.which("claude")
    if exe:
        return exe
    for c in [Path.home() / ".local" / "bin" / "claude",
              Path.home() / ".npm-global" / "bin" / "claude"]:
        if c.exists():
            return str(c)
    return None


def cli_version(exe: str) -> str:
    try:
        p = subprocess.run([exe, "--version"], capture_output=True, timeout=30)
        return p.stdout.decode(errors="replace").strip()[:120]
    except Exception as exc:  # バージョン取得失敗で測定は止めない
        return f"unknown ({exc})"


def build_prefix(nonce: str) -> str:
    """測定ごとに一意なプレフィックスを作る。

    2026-07-31 の M1 で判明: 同一プレフィックスは**別セッションでも**プロバイダ側の
    prefix cache にヒットする（rep2/rep3 の init が cache_w=0, cache_r=45,098 になった）。
    これを放置すると「新規セッションが cache_write を払う」前提が崩れ、測定が無効になる。
    キャッシュはプレフィックス一致で効くため、**先頭行**に一意な nonce を置いて必ず破る。
    """
    return (f"## Project context (resume-probe nonce={nonce})\n"
            + "\n".join(
                f"- probe rule {i:04d}: keep interfaces stable, write focused tests, "
                "never edit files outside declared scope." for i in range(PREFIX_LINES)
            ))


def call(exe: str, prompt: str, label: str, meta: dict,
         resume: str | None = None, model: str | None = None) -> dict:
    cmd = [exe, "--print", "--output-format", "json"]
    if resume:
        cmd += ["--resume", resume]
    if model:
        cmd += ["--model", model]
    t0 = time.time()
    proc = subprocess.run(cmd, input=prompt.encode("utf-8"),
                          capture_output=True, timeout=900)
    rec: dict = {"label": label, "resume": bool(resume), "model_flag": model,
                 "rc": proc.returncode, "wall_s": round(time.time() - t0, 1),
                 "at": time.strftime("%H:%M:%S"),
                 "iso": datetime.now(timezone.utc).astimezone().isoformat(),
                 **meta}
    try:
        data = json.loads(proc.stdout.decode("utf-8", errors="replace"))
        u = data.get("usage") or {}
        rec.update({
            "session_id": data.get("session_id"),
            "input": u.get("input_tokens"),
            "output": u.get("output_tokens"),
            "cache_w": u.get("cache_creation_input_tokens"),
            "cache_r": u.get("cache_read_input_tokens"),
            "cost_usd": data.get("total_cost_usd"),
            "raw": data,
        })
    except Exception as exc:
        rec["parse_error"] = str(exc)
        rec["stderr"] = proc.stderr.decode(errors="replace")[:800]
        rec["stdout_head"] = proc.stdout.decode(errors="replace")[:400]
    with OUT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[{rec['at']}] {label}: rc={rec['rc']} "
          f"in={rec.get('input')} cache_w={rec.get('cache_w')} "
          f"cache_r={rec.get('cache_r')} cost=${rec.get('cost_usd')}",
          flush=True)
    return rec


def classify(r0: dict, r1: dict) -> tuple[str, int]:
    """PROBE_PLAN §2 の分類規則。H = 直前の P0 の (cache_write + cache_read)。"""
    h = (r0.get("cache_w") or 0) + (r0.get("cache_r") or 0)
    if h <= 0:
        return "unknown", h
    if (r1.get("cache_r") or 0) >= WARM_RATIO * h:
        return "warm", h
    if (r1.get("cache_w") or 0) >= WARM_RATIO * h:
        return "cold", h
    return "ambiguous", h


def measure_one(exe: str, mode: str, rep: int,
                gap_s: float, model: str | None, cli_ver: str) -> dict | None:
    """1測定 = 1新規セッション + 一意プレフィックス。

    - 新規セッション: resume がキャッシュ寿命を延長するため（cold 境界の過大評価を防ぐ）
    - 一意プレフィックス: 別セッション間の prefix cache ヒットを防ぐ（2026-07-31 実測）
    """
    nonce = uuid.uuid4().hex[:12]
    prefix = build_prefix(nonce)
    base = {"mode": mode, "rep": rep, "gap_planned_s": gap_s,
            "cli_version": cli_ver, "prefix_lines": PREFIX_LINES, "nonce": nonce}

    r0 = call(exe, prefix + "\n## Q\nReply exactly: OK-1",
              f"{mode}_r{rep}_init", base)
    sid = r0.get("session_id")
    if not sid or r0["rc"] != 0:
        print(f"[SKIP] {mode} rep{rep}: initial call failed", file=sys.stderr, flush=True)
        return None

    t_gap0 = time.time()
    if gap_s > 0:
        print(f"[WAIT] {gap_s:.0f}s (mode={mode} rep={rep})...", flush=True)
        time.sleep(gap_s)
    gap_actual = round(time.time() - t_gap0, 1)

    if mode == "xsession":
        # M4: 2本目は resume せず、**同一プレフィックスで新規セッション**を作る。
        # ここで cache_read ≈ H なら別セッション間で prefix cache がヒットしている
        # （= γ ≈ α_r。【A1】反証）。cache_write ≈ H なら当初 A1 どおり（γ = 1）。
        r1 = call(exe, prefix + "\n## Q\nReply exactly: OK-2",
                  f"{mode}_r{rep}_second", {**base, "gap_actual_s": gap_actual})
    else:
        r1 = call(exe, "Reply exactly: OK-2", f"{mode}_r{rep}_resume",
                  {**base, "gap_actual_s": gap_actual}, resume=sid, model=model)

    verdict, h = classify(r0, r1)
    summary = {"label": f"{mode}_r{rep}_verdict", "iso": datetime.now(timezone.utc).astimezone().isoformat(),
               "mode": mode, "rep": rep, "gap_planned_s": gap_s,
               "gap_actual_s": gap_actual, "H": h, "verdict": verdict,
               "cache_r_resume": r1.get("cache_r"), "cache_w_resume": r1.get("cache_w"),
               "cost_init_usd": r0.get("cost_usd"), "cost_resume_usd": r1.get("cost_usd"),
               "cli_version": cli_ver, "model_flag": model, "nonce": nonce}
    if r0.get("cost_usd") and r1.get("cost_usd"):
        summary["cost_ratio_resume_over_init"] = round(r1["cost_usd"] / r0["cost_usd"], 4)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(summary, ensure_ascii=False) + "\n")
    note = ""
    if mode == "xsession":
        note = ("  [warm=クロスセッションヒット(γ≈α_r・A1反証) / "
                "cold=ヒットなし(γ=1・A1どおり)]")
    print(f"  -> verdict={verdict} H={h:,} gap_actual={gap_actual:.0f}s "
          f"cost_ratio={summary.get('cost_ratio_resume_over_init')}{note}", flush=True)
    return summary


def run_legacy(exe: str, cli_ver: str) -> int:
    """旧来の単一セッション連続測定（既存結果の再現用。cold境界の測定には使わない）。"""
    prefix = build_prefix(uuid.uuid4().hex[:12])
    base = {"mode": "legacy", "cli_version": cli_ver}
    r1 = call(exe, prefix + "\n## Q\nReply exactly: OK-1", "P0_initial", base)
    sid = r1.get("session_id")
    if not sid or r1["rc"] != 0:
        return 1
    call(exe, "Reply exactly: OK-2", "P1_warm_resume", base, resume=sid)
    print("[WAIT] 380s...", flush=True)
    time.sleep(380)
    call(exe, "Reply exactly: OK-3", "P2_cold_resume", base, resume=sid)
    call(exe, "Reply exactly: OK-4", "P3_model_switch_resume", base,
         resume=sid, model="haiku")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="resume/TTL probe (1 measurement = 1 fresh session)")
    ap.add_argument("--mode", choices=["warm", "gap", "switch", "xsession", "legacy"],
                    default="warm")
    ap.add_argument("--gap-min", type=float, default=0.0, help="mode=gap のギャップ（分）")
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--switch-model", default="haiku", help="mode=switch で切り替える先")
    args = ap.parse_args()

    exe = find_claude()
    if not exe:
        print("[ERROR] claude CLI not found", file=sys.stderr)
        return 1
    ver = cli_version(exe)
    print(f"claude={exe} version={ver} prefix_lines={PREFIX_LINES} "
          f"mode={args.mode} reps={args.reps} gap_min={args.gap_min} "
          f"(prefix nonce per measurement)", flush=True)

    if args.mode == "legacy":
        return run_legacy(exe, ver)

    if args.mode == "gap" and args.gap_min <= 0:
        print("[ERROR] --mode gap には --gap-min が必要", file=sys.stderr)
        return 2

    gap_s = args.gap_min * 60.0 if args.mode == "gap" else 0.0
    model = args.switch_model if args.mode == "switch" else None

    results = []
    for rep in range(1, args.reps + 1):
        s = measure_one(exe, args.mode, rep, gap_s, model, ver)
        if s:
            results.append(s)

    print("\n=== summary ===", flush=True)
    for s in results:
        print(f"  rep{s['rep']}: {s['verdict']:9s} gap={s['gap_actual_s']:.0f}s "
              f"cost_ratio={s.get('cost_ratio_resume_over_init')}", flush=True)
    verdicts = [s["verdict"] for s in results]
    if verdicts:
        warm_n = verdicts.count("warm")
        print(f"  warm {warm_n}/{len(verdicts)}  (PROBE_PLAN §1 の生存割合として報告する)",
              flush=True)
    print(f"raw+verdict: {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
