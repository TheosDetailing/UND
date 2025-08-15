import json
from unittest.mock import patch

from obsidian_note_gen import core


def fake_infer_meta(_):
    return json.dumps(
        {
            "title": "Ancient Bridges",
            "topic": "bridges",
            "topics": ["History & Geography", "Engineering & Technology"],
            "tags": ["architecture", "stone"],
        }
    )


def fake_infer_body(_):
    return "Body text " + ("x" * 1200)


@patch("obsidian_note_gen.core.api_infer", side_effect=[fake_infer_meta(""), fake_infer_body("")])
def test_single_subject(mock_infer, tmp_path):
    delays = core.Delays(meta_to_content=0, between_rows=0)
    path = core.process_subject(
        "Ancient Bridges", api_url="http://example", notes_dir=str(tmp_path), delays=delays
    )
    assert path and (tmp_path / "ancient-bridges.md").exists()
    data = (tmp_path / "ancient-bridges.md").read_text()
    assert 'title: "Ancient Bridges"' in data
    assert "tags: [" in data
    assert "Body text" in data

