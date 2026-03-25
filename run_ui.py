"""Launcher script for the arxiv_hunt Streamlit UI."""

import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Launch the Streamlit app."""
    app_path = Path(__file__).resolve().parent / "ui" / "app.py"
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app_path)],
        check=True,
    )


if __name__ == "__main__":
    main()
