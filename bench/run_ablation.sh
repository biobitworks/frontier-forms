#!/bin/zsh
# Each speedup alone, then together, on the fastest Fireworks models. Results go to results_ablation.jsonl.
SP="${0:A:h}"
PY=/Users/reuben/github/hobby/Job-Applicator/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
OUT="$SP/results_ablation.jsonl"
: > "$OUT"
step() { "$PY" "$SP/bench.py" --provider fireworks "$@" 2>/dev/null | grep '^{' >> "$OUT"; }

MODELS=(
  accounts/fireworks/routers/glm-5p3-fast
  accounts/fireworks/models/glm-5p3-flash
  accounts/fireworks/models/minimax-m3p1-flash
)

for MODEL in $MODELS; do
  step --model $MODEL --form b --trials 5 --mode toolloop --max-turns 60
  step --model $MODEL --form b --trials 5 --mode batched --groups 6
  step --model $MODEL --form b --trials 5 --mode batched --groups 6 --reply lines
  step --model $MODEL --form b --trials 5 --mode batched --groups 6 --writes all
  step --model $MODEL --form b --trials 5 --mode batched --groups 6 --reply lines --writes all
  step --model $MODEL --form a --trials 5 --mode toolloop
  step --model $MODEL --form a --trials 5 --mode batched --groups 6 --reply lines --writes all
done
echo '{"step": "done"}' >> "$OUT"
