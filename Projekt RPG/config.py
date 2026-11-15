from dataclasses import dataclass, field
import os
from pathlib import Path

from dotenv import load_dotenv


# Ścieżki niezależne od katalogu uruchomienia programu.
APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parent
ENV_PATH = REPO_ROOT / ".env"
CHARACTERS_DIR = APP_DIR / "characters"
SAVE_DIR = APP_DIR / "savegame"
PROMPTS_DIR = APP_DIR / "prompts"
CHARACTER_SYSTEM_INSTRUCTION_PATH = PROMPTS_DIR / "generate-character.system.md"
PLOT_SYSTEM_INSTRUCTION_PATH = PROMPTS_DIR / "generate-plot.system.md"
GAME_MASTER_SYSTEM_INSTRUCTION_PATH = PROMPTS_DIR / "game-master.system.md"
START_ADVENTURE_PROMPT_PATH = PROMPTS_DIR / "start_adventure.system.md"

# Domyślne ustawienia generowania i rozmowy.
DEFAULT_MODEL = "gemini-flash-latest"
CHARACTER_GENERATION_MAX_ATTEMPTS = 2
PLOT_GENERATION_MAX_ATTEMPTS = 3
PLOT_REQUEST_TIMEOUT_MS = 60_000
CHAT_TEMPERATURE = 0.8


@dataclass(frozen=True)
class Config:
    """Ustawienia Gemini; brak klucza nie blokuje uruchomienia interfejsu."""

    api_key: str | None = field(repr=False)
    model: str = DEFAULT_MODEL


def load_config() -> Config:
    """Wczytuje ustawienia, zachowując pierwszeństwo zmiennych środowiskowych."""
    load_dotenv(ENV_PATH, override=False)
    return Config(
        api_key=os.getenv("GEMINI_API_KEY", "").strip() or None,
        model=os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_MODEL,
    )
