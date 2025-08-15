# Obsidian Note Generator

Generate Obsidian-friendly notes using a two step process: a metadata call followed by a rich body call.

## Configuration

The tool talks to a local API. Defaults are baked into the code but can be overridden via environment variables or a `.env` file copied from `.env.example`.

* `API_URL` – API endpoint (default `http://192.168.50.4:8787/infer`)
* `NOTES_DIR` – where notes are written
* `PER_REQUEST_DELAY_SECONDS` – spacing between CSV subjects
* `DELAY_BETWEEN_CALLS_SECONDS` – delay between metadata/body calls

## Installation

Install with `pipx` or via Docker.

```bash
pipx install .
# or
pipx run obsidian-note-gen "Ancient Bridges"
```

### Docker

```bash
docker build -t obsidian-note-gen:latest .
docker run --rm -e API_URL=http://192.168.50.4:8787/infer \
  -e NOTES_DIR=/notes \
  -v "$HOME/Notes":/notes \
  obsidian-note-gen:latest "Ancient Bridges"
```

## Usage

Generate a single subject:

```bash
obsidian-note-gen "Ancient Bridges"
```

Or process a CSV of subjects spaced apart by `PER_REQUEST_DELAY_SECONDS`:

```bash
obsidian-note-gen --file subjects.csv
```

The resulting Markdown contains YAML front matter suitable for Obsidian's Properties view.
