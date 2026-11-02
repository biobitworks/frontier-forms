#!/bin/sh
# Incremental, append-only publication of PUBLIC per-case bits as arms complete.
# Usage: push_results.sh <private_dir> <lane_glob e.g. S-*>   (run from the red-team clone)
# Only redteam/results/bits_*.jsonl and summary_*.json are staged. Gold/raw stay private.
P="$1"; G="$2"; PY="${PY:-python3}"
set -e
git pull -q --rebase origin redteam/claude-fcg-local-ablation-20261102
for f in $P/out_$G.jsonl; do
  [ -s "$f" ] && $PY redteam/analyze.py export --private "$f" --results redteam/results
done
git add redteam/results/bits_*.jsonl redteam/results/summary_*.json
if git diff --cached --quiet; then echo NO_CHANGE; exit 0; fi
n=$(cat redteam/results/bits_*.jsonl | wc -l | tr -d ' ')
git commit -q -m "results: incremental public ablation bits ($(hostname -s), $n records total)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_015q5z1zKr1rBHbSRyNW2L18"
for i in 1 2 3 4; do git pull -q --rebase origin redteam/claude-fcg-local-ablation-20261102 && git push -q origin HEAD:redteam/claude-fcg-local-ablation-20261102 && echo PUSHED && exit 0; sleep $((i*2)); done
exit 1
