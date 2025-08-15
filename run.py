"""Run the Obsidian Note Generator web UI without installing the package."""

from pathlib import Path
import sys

# Add the src directory to the Python path so imports work from a source checkout
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from obsidian_note_gen.webapp import main

if __name__ == "__main__":
    main()
