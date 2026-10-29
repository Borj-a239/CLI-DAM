"""Arrancador sin instalación: `python3 dam.py go ...`.

Cuando instales el paquete (`pip install .`) tendrás el binario real `_dam`
y el wrapper `dam` de dam.bash; este script es solo para probar sin pip.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dam.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
