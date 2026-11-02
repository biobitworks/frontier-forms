#!/bin/zsh
# Downloads Liquid AI GGUFs to ~/models/lfm side by side, checks each SHA-256, then runs the benchmark
# on each through llama-server. Results are appended to results_lfm.jsonl.
SP="${0:A:h}"
PY=/Users/reuben/github/hobby/Job-Applicator/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
OUT="$SP/results_lfm.jsonl"
DIR=~/models/lfm
mkdir -p "$DIR"

# Arguments are repo:file pairs. LFM2.5-2.6B reasons before it answers even with enable_thinking off,
# so every server starts with reasoning disabled.
MODELS=("$@")

fetch() {  # repo file
  local want got
  want=$(curl -s "https://huggingface.co/api/models/LiquidAI/$1/tree/main" | "$PY" -c "
import json, sys
print(next(f['lfs']['oid'] for f in json.load(sys.stdin) if f['path'] == sys.argv[1]))" "$2")
  curl -sSL -C - -o "$DIR/$2" "https://huggingface.co/LiquidAI/$1/resolve/main/$2"
  got=$(shasum -a 256 "$DIR/$2" | cut -d' ' -f1)
  [[ -n "$want" && "$want" == "$got" ]]
}

serve() {  # file
  llama-server -m "$DIR/$1" --host 127.0.0.1 --port 8099 -ngl 99 -c 16384 -np 1 --jinja --no-webui --reasoning off > "$SP/llama_lfm.log" 2>&1 &
  SERVER=$!
  for _ in {1..120}; do
    curl -s -m 1 http://127.0.0.1:8099/health | grep -q ok && return 0
    kill -0 $SERVER 2>/dev/null || return 1
    sleep 1
  done
  return 1
}

step() { "$PY" "$SP/bench.py" --provider llama "$@" 2>/dev/null | grep '^{' >> "$OUT"; }

# A marker file reports each download, because `wait` can't see a function started with `&` here.
for entry in $MODELS; do
  file=${entry##*:}
  rm -f "$DIR/$file.ok" "$DIR/$file.failed"
  { fetch "${entry%%:*}" "$file" && touch "$DIR/$file.ok" || touch "$DIR/$file.failed"; } &
done

for entry in $MODELS; do
  repo=${entry%%:*} file=${entry##*:} name=${file%.gguf}-no-reasoning
  until [[ -e "$DIR/$file.ok" || -e "$DIR/$file.failed" ]]; do sleep 5; done
  if [[ -e "$DIR/$file.failed" ]]; then
    echo "{\"model\": \"$name\", \"failed\": \"download or checksum\"}" >> "$OUT"
    continue
  fi
  if ! serve "$file"; then
    echo "{\"model\": \"$name\", \"failed\": \"server\", \"log\": \"$(tail -1 "$SP/llama_lfm.log" | tr -d '"\\' | cut -c1-200)\"}" >> "$OUT"
    continue
  fi
  step --model "$name" --mode toolloop --form a --trials 1
  step --model "$name" --mode streamed --form a --trials 1
  step --model "$name" --mode streamed --form b --batch 4 --trials 1
  PYTHONPATH="$SP" "$PY" "$SP/tiny.py" --llama --model "$name" --facts 6 2>/dev/null | grep '^{' >> "$OUT"
  kill $SERVER; wait $SERVER 2>/dev/null
done
rm -f "$SP/llama_lfm.log" "$DIR"/*.ok "$DIR"/*.failed
echo '{"step": "done"}' >> "$OUT"
