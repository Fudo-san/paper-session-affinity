#!/usr/bin/env python3
"""A11 検証: stream-json の per-turn 総和が result の合計と一致するか.

sec3 §3.2【A2】訂正記録は「stream-json の assistant イベント usage の総和が
result の合計と正確に一致する」と述べている（実測済み）。A11 の実装が
その性質を保っているか、および H の軌跡が取れているかを確認する。

json モード（既定）と stream-json モードを同一プロンプトで走らせ、
- json モード: 従来どおり turns は空・num_turns は None
- stream-json: per-turn が埋まり、総和が合計と一致する
ことを確かめる。
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

FRAMEWORK = "/home/fudo1/project/旧agent-framework"
sys.path.insert(0, FRAMEWORK)

from fwcore.metrics import CallUsage  # noqa: E402
from mk2_backends import ClaudeCliBackend  # noqa: E402

PROMPT = (
    "次を順に実行すること。"
    "(1) a11probe_a.txt を作り one と書く。"
    "(2) その内容を読む。"
    "(3) a11probe_b.txt を作り two と書く。"
    "完了したら DONE とだけ返す。"
)


async def main() -> int:
    workdir = Path("/tmp/a11probe")
    workdir.mkdir(parents=True, exist_ok=True)
    ok = True

    for stream in (False, True):
        backend = ClaudeCliBackend(stream_json=stream)
        result = await backend.invoke(
            "probe", PROMPT, ["Read", "Write"], workdir, model="haiku"
        )
        usage = CallUsage.from_cli_json(result.raw_json or {})
        label = "stream-json" if stream else "json"
        print(f"\n=== {label} ===")
        print(f"  rc={result.returncode}  num_turns={usage.num_turns}  "
              f"observed_turns={len(usage.turns)}")
        print(f"  合計: in={usage.input_tokens} out={usage.output_tokens} "
              f"cr={usage.cache_read_tokens} cw={usage.cache_creation_tokens} "
              f"cost=${usage.cost_usd}")

        if not stream:
            if usage.turns:
                print("  [NG] json モードで turns が埋まっている（既定は空であるべき）")
                ok = False
            else:
                print("  [OK] json モードは従来どおり（turns 空・後方互換）")
            continue

        if not usage.turns:
            print("  [NG] stream-json なのに per-turn が取れていない")
            ok = False
            continue

        # 入力側のみ一致を要求する。output_tokens は per-event では未確定
        # （message 開始時点の値）であり、確定値は result 側にしかない。
        sums = {
            "input_tokens": sum(t["input_tokens"] for t in usage.turns),
            "cache_read_tokens": sum(t["cache_read_tokens"] for t in usage.turns),
            "cache_creation_tokens": sum(t["cache_creation_tokens"] for t in usage.turns),
        }
        print(f"  per-turn 総和（入力側）: {sums}")
        for key, total in sums.items():
            actual = getattr(usage, key)
            mark = "OK" if total == actual else "NG"
            if total != actual:
                ok = False
            print(f"  [{mark}] {key}: 総和={total} 合計={actual}")

        if usage.num_turns is not None and len(usage.turns) != usage.num_turns:
            print(f"  [NG] 観測ターン数 {len(usage.turns)} が num_turns "
                  f"{usage.num_turns} と一致しない（重複排除の漏れ）")
            ok = False
        else:
            print(f"  [OK] 観測ターン数 = num_turns = {usage.num_turns}")

        trajectory = [t["context_tokens"] for t in usage.turns]
        print(f"  文脈の軌跡 H: {trajectory}")
        print(f"  peak_context_tokens = {usage.peak_context_tokens}")
        if usage.peak_context_tokens and trajectory:
            print("  [OK] H の軌跡が観測できる（R1 の較正・C′ の閾値判定に使える）")

    print("\n判定:", "合格" if ok else "不合格")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
