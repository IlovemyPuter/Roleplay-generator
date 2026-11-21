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

# --- Dostawcy LLM ---------------------------------------------------------
# Wybór dostawcy: zmienna środowiskowa LLM_PROVIDER = gemini | openrouter | ollama
DEFAULT_PROVIDER = "gemini"
SUPPORTED_PROVIDERS = ("gemini", "openrouter", "ollama")

DEFAULT_OPENROUTER_MODEL = "openrouter/auto"
DEFAULT_OLLAMA_MODEL = "llama3.1"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
# Modele lokalne bywają wolne (zwłaszcza na CPU), więc dostają dłuższy timeout.
DEFAULT_OLLAMA_TIMEOUT_MS = 300_000


@dataclass(frozen=True)
class Config:
    """Ustawienia aktywnego dostawcy LLM; brak klucza nie blokuje uruchomienia interfejsu.

    Pola api_key / model / base_url dotyczą dostawcy wybranego w `provider`,
    dzięki czemu reszta kodu nie musi wiedzieć, z którego dostawcy korzysta.
    """

    api_key: str | None = field(default=None, repr=False)
    model: str = DEFAULT_MODEL
    provider: str = DEFAULT_PROVIDER
    base_url: str | None = None
    timeout_ms: int | None = None


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def _env_int(name: str) -> int | None:
    value = _env(name)
    try:
        return int(value) if value else None
    except ValueError:
        return None


def load_config() -> Config:
    """Wczytuje ustawienia, zachowując pierwszeństwo zmiennych środowiskowych."""
    load_dotenv(ENV_PATH, override=False)
    provider = (_env("LLM_PROVIDER") or DEFAULT_PROVIDER).lower()
    timeout_ms = _env_int("LLM_TIMEOUT_MS")

    if provider == "openrouter":
        return Config(
            provider=provider,
            api_key=_env("OPENROUTER_API_KEY") or None,
            model=_env("OPENROUTER_MODEL") or DEFAULT_OPENROUTER_MODEL,
            base_url=_env("OPENROUTER_BASE_URL") or DEFAULT_OPENROUTER_BASE_URL,
            timeout_ms=timeout_ms,
        )
    if provider == "ollama":
        return Config(
            provider=provider,
            api_key=None,  # Ollama działa lokalnie i nie wymaga klucza
            model=_env("OLLAMA_MODEL") or DEFAULT_OLLAMA_MODEL,
            base_url=_env("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_BASE_URL,
            timeout_ms=timeout_ms or DEFAULT_OLLAMA_TIMEOUT_MS,
        )
    # gemini (domyślnie) – nieznana nazwa dostawcy zostanie zgłoszona przez create_provider()
    return Config(
        provider=provider,
        api_key=_env("GEMINI_API_KEY") or None,
        model=_env("GEMINI_MODEL") or DEFAULT_MODEL,
        timeout_ms=timeout_ms,
    )
