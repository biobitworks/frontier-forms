"""Contain one Pi run. A model with a shell must not reach secrets, the gold answers, or anything outside its run dir.

Pi gets a minimal environment (only the Fireworks key, never the rest of .env) and runs under a sandbox-exec
profile that denies reads of credentials and of the benchmark's gold labels, and denies writes outside the run dir.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
REPO = BENCH.parent
HOME = Path.home()
NODE_DIR = str(Path("/Users/reuben/.local/bin"))

DENY_READ = [REPO / ".env", REPO / ".git", BENCH / "harness", BENCH / "results", HOME / ".ssh", HOME / ".aws",
             HOME / ".config", HOME / ".pi", HOME / ".claude", HOME / ".gnupg", HOME / ".npmrc", HOME / ".netrc",
             HOME / "Library/Keychains", HOME / "Library/Application Support/Google/Chrome",
             HOME / "Library/Cookies"]


def fireworks_key() -> str:
    for line in (REPO / ".env").read_text().splitlines():
        match = re.match(r"\s*FIREWORKS_API_KEY\s*=\s*(.*)$", line)
        if match:
            return match[1].strip().strip("\"'")
    raise SystemExit("FIREWORKS_API_KEY is not in .env")


def profile(run_dir: Path, agent_dir: Path) -> str:
    denied = "\n".join(f'  (subpath "{path}")' for path in DENY_READ)
    return f"""(version 1)
(allow default)
(deny file-read*
{denied})
(deny file-write*)
(allow file-write*
  (subpath "{run_dir.resolve()}")
  (subpath "{agent_dir.resolve()}")
  (subpath "/private/tmp")
  (subpath "/private/var/folders")
  (literal "/dev/null")
  (literal "/dev/tty")
  (regex #"^/dev/ttys[0-9]+$"))
(allow process-exec (literal "/bin/ps") (with no-sandbox))
"""


def child_env(extra: dict[str, str] | None = None, agent_dir: Path | None = None) -> dict[str, str]:
    home = (agent_dir / "home") if agent_dir else HOME  # throwaway, so a skill's installs never reach the real home
    home.mkdir(exist_ok=True)
    return {"PATH": f"{BENCH / 'pi/node_modules/.bin'}:{NODE_DIR}:/usr/bin:/bin", "HOME": str(home), "LANG": "en_US.UTF-8",
            "TMPDIR": "/private/tmp", "FIREWORKS_API_KEY": fireworks_key(), "PI_OFFLINE": "1",
            "PI_SKIP_VERSION_CHECK": "1", "PI_TELEMETRY": "0",
            **({"PI_CODING_AGENT_DIR": str(agent_dir)} if agent_dir else {}), **(extra or {})}


def run_pi(args: list[str], run_dir: Path, agent_dir: Path, **options) -> tuple[int | None, bool]:
    return run_contained([str(BENCH / "pi/node_modules/.bin/pi"), *args], run_dir, agent_dir, **options)


def run_contained(command: list[str], run_dir: Path, agent_dir: Path, *, timeout: float, extra_env: dict[str, str] | None = None,
                  stdout, stderr) -> tuple[int | None, bool]:
    """Every arm runs through here. Returns (exit code, timed out). A timed-out run is killed and scored on whatever it left."""
    rules = run_dir / ".sandbox.sb"
    rules.write_text(profile(run_dir, agent_dir))
    proc = subprocess.Popen(["/usr/bin/sandbox-exec", "-f", str(rules), *command], cwd=run_dir, env=child_env(extra_env, agent_dir), stdout=stdout, stderr=stderr,
                            stdin=subprocess.DEVNULL)
    try:
        return proc.wait(timeout=timeout), False
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        return None, True
