"""
Reads and validates a bot's manifest.json. The contract a bot's folder
must satisfy to be added to the panel:

{
  "name": "Twitter to Telegram Bot",
  "entrypoint": "bot.py",
  "venv": "venv",
  "description": "Optional, shown in the UI."
}

folder_path itself is not stored in the manifest - it's implicit: wherever
the manifest lives is the bot's working directory.
"""

import json
from pathlib import Path

REQUIRED_FIELDS = ("name", "entrypoint", "venv")


class ManifestError(Exception):
    pass


def read_manifest(folder_path: str) -> dict:
    manifest_path = Path(folder_path) / "manifest.json"
    if not manifest_path.exists():
        raise ManifestError(f"No manifest.json found in {folder_path}")

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ManifestError(f"manifest.json is not valid JSON: {e}")

    missing = [f for f in REQUIRED_FIELDS if not data.get(f)]
    if missing:
        raise ManifestError(f"manifest.json is missing required field(s): {', '.join(missing)}")

    entry_path = Path(folder_path) / data["entrypoint"]
    if not entry_path.exists():
        raise ManifestError(f"entrypoint '{data['entrypoint']}' not found in {folder_path}")

    return {
        "static_name": data["name"],
        "entrypoint": data["entrypoint"],
        "venv_dir": data["venv"],
        "description": data.get("description", ""),
    }
