#!/usr/bin/env bash
# 実験用 worktree の後片付け。
#
# run_experiment.py は spec×arm×rep ごとに worktree を作る。spec の `repo` は
# 仕様ごとに異なりうる（旧agent-framework / square-media …）ので、
# **1つのリポジトリだけを掃除すると取り残しが出る**（2026-08-01 に実際に発生）。
# 既定で実験に使う全リポジトリを対象にする。
set -u
REPOS=("$HOME/project/旧agent-framework" "$HOME/project/square-media")
[ $# -gt 0 ] && REPOS=("$@")

for REPO in "${REPOS[@]}"; do
  [ -d "$REPO/.git" ] || continue
  echo "=== $REPO ==="
  git -C "$REPO" worktree list --porcelain \
    | sed -n 's/^worktree //p' \
    | grep -E '^/tmp/(paper_|m5_arm)' \
    | while IFS= read -r w; do
        echo "  remove $w"
        git -C "$REPO" worktree remove --force "$w" 2>/dev/null || rm -rf "$w"
      done
  git -C "$REPO" worktree prune
  git -C "$REPO" worktree list
done

rm -rf /tmp/paper_* 2>/dev/null || true
echo "=== 完了 ==="
