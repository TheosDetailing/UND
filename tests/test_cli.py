import json
from unittest.mock import patch

from obsidian_note_gen import cli


def fake_infer_meta(prompt: str) -> str:
    return json.dumps(
        {
            "title": "Ancient Bridges",
            "topic": "bridges",
            "topics": ["History & Geography", "Engineering & Technology"],
            "tags": ["architecture", "stone"],
        }
    )


def fake_infer_body(prompt: str) -> str:
    return "Body text " + ("x" * 1200)


@patch(
    "obsidian_note_gen.cli.api_infer",
    side_effect=[fake_infer_meta(""), fake_infer_body("")],
)
def test_single_subject(mock_infer, tmp_path, monkeypatch):
    monkeypatch.setenv("NOTES_DIR", str(tmp_path))
    monkeypatch.setenv("DELAY_BETWEEN_CALLS_SECONDS", "0")
    path = cli.process_subject("Ancient Bridges")
    assert path and (tmp_path / "ancient-bridges.md").exists()
    data = (tmp_path / "ancient-bridges.md").read_text()
    assert 'title: "Ancient Bridges"' in data
    assert "tags: [" in data
    assert "Body text" in data
