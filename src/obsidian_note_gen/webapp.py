from __future__ import annotations

"""Flask web UI for the note generator."""

from pathlib import Path
import webbrowser
from flask import Flask, jsonify, render_template, request

from .config import load_config, save_config
from .core import Delays, process_csv, process_subject


BASE_DIR = Path(__file__).resolve().parent
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)


def _config_from_request(cfg: dict) -> tuple[str, str, Delays]:
    api_url = request.form.get("api_url") or cfg["api_url"]
    notes_dir = request.form.get("notes_dir") or cfg["notes_dir"]
    delay_meta = int(request.form.get("delay_meta_content") or cfg["delay_meta_content"])
    delay_rows = int(request.form.get("delay_between_rows") or cfg["delay_between_rows"])
    new_cfg = {
        "api_url": api_url,
        "notes_dir": notes_dir,
        "delay_meta_content": delay_meta,
        "delay_between_rows": delay_rows,
    }
    save_config(new_cfg)
    return api_url, notes_dir, Delays(delay_meta, delay_rows)


@app.get("/")
def index():
    cfg = load_config()
    return render_template("index.html", config=cfg)


@app.post("/run-one")
def run_one():
    cfg = load_config()
    api_url, notes_dir, delays = _config_from_request(cfg)
    subject = request.form.get("subject", "")
    path = process_subject(subject, api_url=api_url, notes_dir=notes_dir, delays=delays)
    return jsonify({"path": path})


@app.post("/upload")
def upload_csv():
    cfg = load_config()
    api_url, notes_dir, delays = _config_from_request(cfg)
    file = request.files.get("file")
    if not file:
        return jsonify({"paths": []})
    paths = process_csv(file.stream, api_url=api_url, notes_dir=notes_dir, delays=delays)
    return jsonify({"paths": paths})


def main() -> None:
    cfg = load_config()
    url = "http://127.0.0.1:8789"
    print(f"Open {url}")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    app.run(port=8789)


if __name__ == "__main__":
    main()

