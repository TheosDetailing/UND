# Obsidian Note Generator

Generate Obsidian-friendly notes using a two step process: a metadata call
followed by a rich body call. A small web UI lets you drag-and-drop a CSV of
subjects or type a single subject.

## Quick start

### Install as a command

Install with [`pipx`](https://pypa.github.io/pipx/) (recommended) or regular `pip`:

```bash
pipx install git+https://github.com/<you>/obsidian-note-gen.git
# or
pip install git+https://github.com/<you>/obsidian-note-gen.git
```

Run the app:

```bash
obsidian-note-gen
```

### Run from a source checkout

To run without installing the package globally:

```bash
git clone https://github.com/<you>/obsidian-note-gen.git
cd obsidian-note-gen
python -m venv .venv
source .venv/bin/activate  # on Windows use ".venv\\Scripts\\activate"
pip install -r requirements.txt
python run.py
```

The app opens `http://127.0.0.1:8789` in your browser (or prints the URL). Set your
API URL and notes directory in the UI, then either type a subject or
drag-and-drop a CSV file (first column = subject). The application waits 30 s
between the metadata and body calls and 120 s between CSV rows by default.

The API is expected to return JSON envelopes like:

```json
{"ok": true, "output": "..."}
```

Generated Markdown notes contain YAML front matter compatible with
Obsidian's Properties view.

