#!/usr/bin/env bash
# 実験用 worktree の後片付け。
# run_experiment.py は spec×arm×rep ごとに worktree を作るため、
# 実験後に残る。放置すると次回の worktree add が汚れるので明示的に掃除する。
set -u
REPO="${1:-$HOME/project/旧agent-framework}"

echo "=== 除去対象 ==="
git -C "$REPO" worktree list --porcelain \
  | sed -n 's/^worktree //p' \
  | grep -E '^/tmp/(paper_runs|m5_arm)' || echo "(なし)"

git -C "$REPO" worktree list --porcelain \
  | sed -n 's/^worktree //p' \
  | grep -E '^/tmp/(paper_runs|m5_arm)' \
  | while IFS= read -r w; do
      git -C "$REPO" worktree remove --force "$w" 2>/dev/null || rm -rf "$w"
    done

git -C "$REPO" worktree prune
echo "=== 残存 ==="
git -C "$REPO" worktree list
