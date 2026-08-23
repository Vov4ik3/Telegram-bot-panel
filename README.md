# Bot Panel

A small local web dashboard for starting, stopping, and monitoring your own
Python bots as separate processes. Each bot stays completely independent —
its own folder, its own venv, its own dependencies — the panel just
supervises the process.

## How a bot becomes manageable

Drop a `manifest.json` in the bot's own folder (see `manifest.example.json`):

```json
{
  "name": "Twitter to Telegram Bot",
  "entrypoint": "bot.py",
  "venv": "venv",
  "description": "Optional, shown in the UI."
}
```

- `name` — what the bot calls itself. Not required to be unique.
- `entrypoint` — the script to run, relative to the bot's own folder.
- `venv` — the venv folder name (also relative). The panel resolves the
  actual interpreter itself (`venv/Scripts/python.exe` on Windows,
  `venv/bin/python` on Linux), so the same manifest works unmodified on
  either OS.
- `description` — optional, shown under the bot's name in the list.

No working-directory field — wherever `manifest.json` lives *is* the bot's
working directory. That's deliberate: it's a direct fix for the exact
mistake Task Scheduler makes easy (launching a script from the wrong `cwd`,
so it can't find its own `.env`).

## Setup

```bash
python -m venv venv
venv\Scripts\activate      # or: source venv/bin/activate  on Linux
pip install -r requirements.txt
python app.py
```

Then open `http://127.0.0.1:5000`.

## Using it

- **Add a bot** — give it the folder path containing `manifest.json`. If the
  name's already taken by another registered bot, you'll be asked for a
  different display name (the manifest's own name isn't touched).
- **Start / Stop** — spawns or terminates the bot's process directly.
- **Rename** — only changes what you see in the panel; doesn't touch
  anything in the bot's own files.
- **Delete** — removes it from the panel (stopping it first if running).
  Doesn't delete the bot's files.
- Click a bot's row to expand its detail — folder, entrypoint, and a tail of
  its recent log output.

## Status meanings

| Glyph | Status | Meaning |
|---|---|---|
| ● green | online | Process is running |
| ○ grey | offline | Not running — either never started, or you stopped it |
| ✕ red | crashed | Was running, exited unexpectedly. Log tail shown. |
| ⚠ red | launch_failed | Couldn't even start (bad interpreter/entrypoint path) |

## How output is captured

Each bot's stdout/stderr is redirected to `panel_run.log` inside its own
folder (append mode) rather than piped directly into the panel — piping
risks a deadlock if a bot ever logs more than the OS pipe buffer holds
while nothing's actively draining it. The log file sidesteps that, and
doubles as what you see in the detail view and in a crash's captured
output.

## Known limitations (v1)

- If the panel itself restarts while a bot is running, that bot keeps
  running (nothing kills it), but the panel loses its process handle and
  shows stale status until you interact with it again.
- No auto-start-on-panel-launch — you start each bot manually after the
  panel comes up.
- Manifest only — no auto-detection/scaffolding for bots that don't have
  one yet.
- Single local machine only — no remote/multi-server support.
