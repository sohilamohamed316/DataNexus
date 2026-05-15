"""
src/cli/__main__.py
====================
Makes the CLI runnable as a module without installation:

    python -m src.cli <command>
    python -m src.cli seed
    python -m src.cli run 1
    python -m src.cli --help
"""

from src.cli.main import cli

if __name__ == "__main__":
    cli()
