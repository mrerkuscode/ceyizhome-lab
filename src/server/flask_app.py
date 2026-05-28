"""
CeyizHome Lab — Browser Mode Server (Sprint 1)

Usage:
    cd production-bot
    .venv\\Scripts\\python.exe -m src.server.flask_app

Then open: http://localhost:8000
Desktop mode (start_app.bat) is unaffected by this server.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is on the path so all webui_backend imports resolve
_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from flask import Flask, send_from_directory

from server.routes import api_bp

_WEBUI_DIR = (_SRC / "webui").resolve()

app = Flask(__name__, static_folder=str(_WEBUI_DIR), static_url_path="")

# Register API routes under /api
app.register_blueprint(api_bp)


@app.route("/")
def index():
    return send_from_directory(str(_WEBUI_DIR), "index.html")


# Serve any webui asset (CSS, JS, fonts, etc.)
@app.route("/<path:filename>")
def webui_asset(filename: str):
    return send_from_directory(str(_WEBUI_DIR), filename)


if __name__ == "__main__":
    print("=" * 56)
    print("CeyizHome Lab — Browser Mode")
    print("Tarayicidan acin: http://localhost:8000")
    print("Durdurmak icin:   Ctrl+C")
    print("=" * 56)
    app.run(host="127.0.0.1", port=8000, debug=False)
