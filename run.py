"""Run the Obsidian Note Generator web UI without installing the package."""

from pathlib import Path
import subprocess
import sys

BASE_DIR = Path(__file__).resolve().parent


def auto_update() -> None:
    """Fetch updates from the remote repository."""
    try:
        subprocess.run(["git", "pull"], cwd=BASE_DIR, check=True)
    except Exception as exc:  # pragma: no cover - best effort
        print(f"Auto-update skipped: {exc}")


# Add the src directory to the Python path so imports work from a source checkout
sys.path.insert(0, str(BASE_DIR / "src"))

from obsidian_note_gen.webapp import main


if __name__ == "__main__":
    auto_update()
    main()
