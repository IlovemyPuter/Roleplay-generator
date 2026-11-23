from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent

# Dodajemy katalog główny repozytorium oraz wszystkie podkatalogi zawierające pliki .py
sys.path.insert(0, str(REPO_ROOT))

for py_file in REPO_ROOT.rglob("turning_point.py"):
    parent_str = str(py_file.parent)
    if parent_str not in sys.path:
        sys.path.insert(0, parent_str)
