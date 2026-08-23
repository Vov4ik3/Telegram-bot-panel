from flask import Flask, jsonify, render_template, request

import db
import process_manager
from manifest import ManifestError, read_manifest

app = Flask(__name__)
db.init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/bots", methods=["GET"])
def list_bots():
    bots = db.list_bots()
    result = []
    for bot in bots:
        bot["status"] = process_manager.refresh_status(bot)
        fresh = db.get_bot(bot["id"])
        if fresh is None:
            continue  # deleted concurrently (e.g. delete click racing the poll)
        bot["last_error"] = fresh["last_error"]
        result.append(bot)
    return jsonify(result)


@app.route("/api/bots", methods=["POST"])
def add_bot():
    payload = request.get_json(force=True, silent=True) or {}
    folder_path = (payload.get("folder_path") or "").strip()
    custom_name = (payload.get("display_name") or "").strip()

    if not folder_path:
        return jsonify({"error": "folder_path is required."}), 400

    try:
        info = read_manifest(folder_path)
    except ManifestError as e:
        return jsonify({"error": str(e)}), 400

    display_name = custom_name or info["static_name"]
    if db.display_name_taken(display_name):
        return jsonify({
            "error": f"Name '{display_name}' is already in use. Pick a different display name.",
            "needs_display_name": True,
        }), 409

    bot_id = db.add_bot(
        static_name=info["static_name"],
        display_name=display_name,
        folder_path=folder_path,
        entrypoint=info["entrypoint"],
        venv_dir=info["venv_dir"],
        description=info["description"],
    )
    return jsonify(db.get_bot(bot_id)), 201


@app.route("/api/bots/<int:bot_id>/start", methods=["POST"])
def start_bot(bot_id):
    bot = db.get_bot(bot_id)
    if not bot:
        return jsonify({"error": "No such bot."}), 404
    ok, message = process_manager.start_bot(bot)
    return jsonify({"ok": ok, "message": message, "bot": db.get_bot(bot_id)})


@app.route("/api/bots/<int:bot_id>/stop", methods=["POST"])
def stop_bot(bot_id):
    bot = db.get_bot(bot_id)
    if not bot:
        return jsonify({"error": "No such bot."}), 404
    ok, message = process_manager.stop_bot(bot_id)
    return jsonify({"ok": ok, "message": message, "bot": db.get_bot(bot_id)})


@app.route("/api/bots/<int:bot_id>", methods=["PATCH"])
def rename_bot(bot_id):
    bot = db.get_bot(bot_id)
    if not bot:
        return jsonify({"error": "No such bot."}), 404

    payload = request.get_json(force=True, silent=True) or {}
    new_name = (payload.get("display_name") or "").strip()
    if not new_name:
        return jsonify({"error": "display_name is required."}), 400
    if db.display_name_taken(new_name, exclude_id=bot_id):
        return jsonify({"error": f"Name '{new_name}' is already in use."}), 409

    db.rename_bot(bot_id, new_name)
    return jsonify(db.get_bot(bot_id))


@app.route("/api/bots/<int:bot_id>", methods=["DELETE"])
def delete_bot(bot_id):
    bot = db.get_bot(bot_id)
    if not bot:
        return jsonify({"error": "No such bot."}), 404
    process_manager.stop_bot(bot_id)
    db.delete_bot(bot_id)
    return jsonify({"ok": True})


@app.route("/api/bots/<int:bot_id>/log", methods=["GET"])
def bot_log(bot_id):
    bot = db.get_bot(bot_id)
    if not bot:
        return jsonify({"error": "No such bot."}), 404
    return jsonify({"log": process_manager.tail_log(bot["folder_path"], n=200)})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
