#!/bin/zsh
# Runs every measurement in order, one model on the GPU at a time. Results go to results.jsonl.
SP="${0:A:h}"
PY=/Users/reuben/github/hobby/Job-Applicator/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$SP"
OUT="$SP/results.jsonl"
: > "$OUT"
step() { echo "{\"step\": \"$*\"}" >> "$OUT"; "$@" 2>/dev/null | grep '^{' >> "$OUT"; }
unload() { curl -s http://127.0.0.1:11434/api/generate -d "{\"model\":\"$1\",\"keep_alive\":0}" > /dev/null; }

BIG=qwen3.8:27b TINY=qwen3.5:0.8b

curl -s http://127.0.0.1:11434/api/generate -d "{\"model\":\"$BIG\",\"prompt\":\"hi\",\"stream\":false,\"think\":false,\"keep_alive\":\"30m\",\"options\":{\"num_predict\":2,\"num_ctx\":8192}}" > /dev/null

# Same 12-field form, three ways, big model.
step $PY "$SP/bench.py" --mode toolloop --model $BIG --form a --trials 2
step $PY "$SP/bench.py" --mode batched  --model $BIG --form a --trials 3
step $PY "$SP/bench.py" --mode streamed --model $BIG --form a --trials 3

# 40 screening questions: nearly all reach the model.
step $PY "$SP/bench.py" --mode batched  --model $BIG --form b --batch 4 --trials 2
step $PY "$SP/bench.py" --mode streamed --model $BIG --form b --batch 4 --trials 2
step $PY "$SP/bench.py" --mode streamed --model $BIG --form b --batch 0 --trials 2
step $PY "$SP/bench.py" --mode toolloop --model $BIG --form b --trials 1 --max-turns 60

# Batch shape and prompt-prefix reuse.
step $PY "$SP/replay.py" --model $BIG --what sequential
step $PY "$SP/replay.py" --model $BIG --what one
step $PY "$SP/replay.py" --model $BIG --what prefix
unload $BIG

# Tiny model: same scripted path, then a narrowed one.
step $PY "$SP/bench.py" --mode toolloop --model $TINY --form a --trials 2
step $PY "$SP/bench.py" --mode streamed --model $TINY --form a --trials 3
step $PY "$SP/bench.py" --mode streamed --model $TINY --form b --batch 4 --trials 2
step $PY "$SP/tiny.py" --model $TINY --facts 6
step $PY "$SP/tiny.py" --model $TINY --facts 10
unload $TINY

# Real concurrency needs a server started with more slots. A private one on another port leaves
# the app's Ollama settings alone.
OLLAMA_HOST=127.0.0.1:11555 OLLAMA_NUM_PARALLEL=3 /Applications/Ollama.app/Contents/Resources/ollama serve > "$SP/ollama3.log" 2>&1 &
PRIVATE=$!
sleep 4
step $PY "$SP/replay.py" --endpoint http://127.0.0.1:11555 --model $BIG --what concurrent --parallel 3
kill $PRIVATE

# Model-driven browser: the existing browser-use eval, thinking at the model's default.
cd /Users/reuben/github/hobby/Job-Applicator
K=ollama step $PY -m evals.fallback.run --key-env K --endpoint http://127.0.0.1:11434/v1 --model $BIG --trials 1 --timeout 420 --max-steps 25
unload $BIG
echo '{"step": "done"}' >> "$OUT"
