#!/bin/zsh
# The same forms on Fireworks serverless models. Results go to results_fireworks.jsonl.
SP="${0:A:h}"
PY=/Users/reuben/github/hobby/Job-Applicator/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
OUT="$SP/results_fireworks.jsonl"
: > "$OUT"
step() { "$PY" "$SP/bench.py" --provider fireworks "$@" 2>/dev/null | grep '^{' >> "$OUT"; }

MODELS=(
  accounts/fireworks/models/qwen3p8-max
  accounts/fireworks/models/qwen3p8-2p4t-a95b
  accounts/fireworks/models/glm-5p3
  accounts/fireworks/models/glm-5p3-flash
  accounts/fireworks/routers/glm-5p3-fast
)

for MODEL in $MODELS; do
  step --model $MODEL --mode toolloop --form a --trials 3
  step --model $MODEL --mode batched  --form a --trials 3
  step --model $MODEL --mode streamed --form a --trials 3
  step --model $MODEL --mode toolloop --form b --trials 2 --max-turns 60
  step --model $MODEL --mode batched  --form b --batch 4 --trials 2
  step --model $MODEL --mode streamed --form b --batch 4 --trials 2
  step --model $MODEL --mode streamed --form b --batch 4 --parallel 4 --trials 2
  step --model $MODEL --mode streamed --form b --batch 4 --parallel 8 --trials 2
  step --model $MODEL --mode streamed --form b --batch 0 --trials 2
done
echo '{"step": "done"}' >> "$OUT"
