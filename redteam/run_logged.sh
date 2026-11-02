#!/bin/sh
# Usage: run_logged.sh <lane> <ledger.jsonl> <private_log> -- cmd args...
# Appends {lane, host, cmd, exit, start, end, log_sha256} to the ledger. The command
# line is recorded verbatim; never pass secrets as arguments.
lane="$1"; ledger="$2"; log="$3"; shift 4
start=$(date -u +%Y-%m-%dT%H:%M:%SZ)
"$@" >"$log" 2>&1; code=$?
end=$(date -u +%Y-%m-%dT%H:%M:%SZ)
sha=$(shasum -a 256 "$log" | cut -d' ' -f1)
cmd=$(printf '%s ' "$@" | sed -e "s#$HOME#~#g" -e 's/"/\\"/g')
printf '{"lane":"%s","host":"%s","start":"%s","end":"%s","exit":%s,"cmd":"%s","log_sha256":"%s"}\n' \
  "$lane" "$(hostname)" "$start" "$end" "$code" "$cmd" "$sha" >> "$ledger"
exit $code
