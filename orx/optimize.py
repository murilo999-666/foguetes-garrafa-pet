"""Ponto de entrada da CLI: python optimize.py <comando> ...

Precisa rodar com o Python da venv do projeto (.venv), onde o pacote orx está
instalado em modo editável.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from orx.cli import main

if __name__ == "__main__":
    sys.exit(main())
