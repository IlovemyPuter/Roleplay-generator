from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import ValidationError

from character import Character

CHARACTERS_DIR = Path(__file__).resolve().parent / "characters"


def ensure_characters_dir() -> Path:
    """Tworzy folder characters, jeśli jeszcze nie istnieje."""
    CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)
    return CHARACTERS_DIR


def character_filename(name: str) -> str:
    """Buduje bezpieczną nazwę pliku na podstawie imienia postaci."""
    slug = re.sub(r"[^\w\-]+", "_", name.strip(), flags=re.UNICODE)
    slug = re.sub(r"_+", "_", slug).strip("._")
    return f"{slug or 'character'}.json"


def save_character(character: Character | dict) -> Path:
    """Zapisuje postać do characters/<nazwa>.json; zwraca ścieżkę pliku."""
    ensure_characters_dir()
    if isinstance(character, Character):
        data = character.model_dump()
    else:
        data = Character.model_validate(character).model_dump()

    path = CHARACTERS_DIR / character_filename(data["name"])
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _load_character_file(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Character.model_validate(data).model_dump()
    except (OSError, json.JSONDecodeError, ValidationError, TypeError) as e:
        print(f"Błąd wczytywania pliku postaci {path}: {e}")
        return None


def load_characters() -> list[dict]:
    """Wczytuje wszystkie poprawne postacie z folderu characters."""
    ensure_characters_dir()
    characters: list[dict] = []
    for path in sorted(CHARACTERS_DIR.glob("*.json")):
        character = _load_character_file(path)
        if character is not None:
            characters.append(character)
    return characters
