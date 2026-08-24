"""
Spawns and tracks bot processes. Each bot's stdout/stderr goes to a log file
in its own folder (panel_run.log) rather than a PIPE - piping would risk a
classic deadlock if a bot ever logs more than the OS pipe buffer holds while
nobody's actively draining it. A log file sidesteps that entirely and doubles
as something you can tail when a bot crashes.

State lives in two places on purpose:
- RUNNING (in-memory): the live Popen handle + our own intent for it. Lost on
  panel restart - a bot still running from a previous panel session shows as
  unknown/offline until you interact with it again. Known v1 limitation.
- the database: the last-known status, so the UI has something to show
  immediately on load without waiting for a poll.
"""

import subprocess
import sys
from pathlib import Path

import db

# bot_id -> {"process": Popen, "intent": "running" | "stopped"}
RUNNING = {}

LOG_TAIL_LINES = 40


def resolve_python(folder_path: str, venv_dir: str) -> Path:
    base = Path(folder_path) / venv_dir
    if sys.platform == "win32":
        candidate = base / "Scripts" / "python.exe"
    else:
        candidate = base / "bin" / "python"
    return candidate


def log_path(folder_path: str) -> Path:
    return Path(folder_path) / "panel_run.log"


def clear_log(folder_path: str) -> None:
    path = log_path(folder_path)
    if path.exists():
        path.write_text("", encoding="utf-8")


def tail_log(folder_path: str, n: int = LOG_TAIL_LINES) -> str:
    path = log_path(folder_path)
    if not path.exists():
        return ""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-n:])
    except OSError:
        return ""


def start_bot(bot: dict) -> tuple[bool, str]:
    bot_id = bot["id"]
    existing = RUNNING.get(bot_id)
    if existing and existing["process"].poll() is None:
        return False, "Already running."

    python_path = resolve_python(bot["folder_path"], bot["venv_dir"])
    if not python_path.exists():
        msg = f"Interpreter not found: {python_path}"
        db.update_status(bot_id, "launch_failed", msg)
        return False, msg

    entry_path = Path(bot["folder_path"]) / bot["entrypoint"]
    if not entry_path.exists():
        msg = f"Entrypoint not found: {entry_path}"
        db.update_status(bot_id, "launch_failed", msg)
        return False, msg

    try:
        log_file = open(log_path(bot["folder_path"]), "a", encoding="utf-8")
        process = subprocess.Popen(
            [str(python_path), str(entry_path)],
            cwd=bot["folder_path"],
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
    except OSError as e:
        db.update_status(bot_id, "launch_failed", str(e))
        return False, str(e)

    RUNNING[bot_id] = {"process": process, "intent": "running"}
    db.update_status(bot_id, "online", None)
    return True, "Started."


def stop_bot(bot_id: int) -> tuple[bool, str]:
    entry = RUNNING.get(bot_id)
    if not entry or entry["process"].poll() is not None:
        db.update_status(bot_id, "offline", None)
        return False, "Not running."

    entry["intent"] = "stopped"  # set BEFORE terminating, so the poller
    # reads this as deliberate rather than a crash
    process = entry["process"]
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)

    db.update_status(bot_id, "offline", None)
    return True, "Stopped."


def refresh_status(bot: dict) -> str:
    """Reconcile in-memory process state with the DB. Returns the current status."""
    bot_id = bot["id"]
    entry = RUNNING.get(bot_id)

    if not entry:
        # No process we're tracking. Trust whatever's already in the DB
        # (covers: never started, or started in a previous panel session).
        return bot["status"]

    process = entry["process"]
    returncode = process.poll()

    if returncode is None:
        db.update_status(bot_id, "online", None)
        return "online"

    if entry["intent"] == "stopped":
        db.update_status(bot_id, "offline", None)
    else:
        tail = tail_log(bot["folder_path"])
        msg = f"Exited with code {returncode}.\n{tail}" if tail else f"Exited with code {returncode}."
        db.update_status(bot_id, "crashed", msg)

    del RUNNING[bot_id]
    return db.get_bot(bot_id)["status"]
