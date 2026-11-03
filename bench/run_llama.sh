#!/bin/zsh
# llama-server on the qwen3.8:27b weights Ollama already has. One slot, then three.
SP="${0:A:h}"
PY=/Users/reuben/github/hobby/Job-Applicator/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$SP"
OUT="$SP/results_llama.jsonl"
: > "$OUT"
MANIFEST=~/.ollama/models/manifests/registry.ollama.ai/library/qwen3.8/27b
DIGEST=$($PY -c "import json,sys; print(next(l['digest'] for l in json.load(open(sys.argv[1]))['layers'] if l['mediaType'].endswith('image.model')))" "$MANIFEST")
BLOB=~/.ollama/models/blobs/${DIGEST/:/-}
echo "{\"blob\": \"$BLOB\"}" >> "$OUT"

serve() {  # slots
  llama-server -m "$BLOB" --host 127.0.0.1 --port 8099 -ngl 99 -c $((8192 * $1)) -np "$1" --jinja --no-webui \
    > "$SP/llama_np$1.log" 2>&1 &
  SERVER=$!
  for _ in {1..90}; do
    curl -s -m 1 http://127.0.0.1:8099/health | grep -q ok && return 0
    sleep 1
  done
  return 1
}

for slots in 1 3; do
  if serve $slots; then
    "$PY" "$SP/llama_replay.py" --parallel $slots 2>&1 | grep '^{' >> "$OUT" || echo "{\"failed\": $slots}" >> "$OUT"
  else
    echo "{\"server_failed\": $slots}" >> "$OUT"
  fi
  kill $SERVER; wait $SERVER 2>/dev/null
done
echo '{"step": "done"}' >> "$OUT"
