"""Warstwa abstrakcji nad dostawcami LLM (Gemini, OpenRouter, Ollama).

Reszta aplikacji (main.py, generate_plot.py, generate_character.py, interface.py)
korzysta wyłącznie z interfejsu zdefiniowanego tutaj i nie importuje żadnego SDK:

    provider = create_provider()                       # wg LLM_PROVIDER z .env
    text = provider.generate_text(                     # pojedyncze zapytanie (opcjonalnie JSON)
        "...", system_instruction="...", json_schema=Model.model_json_schema()
    )
    chat = provider.start_chat(system_instruction, history=history_from_clean(h))
    for chunk in chat.send_message_stream("..."):      # strumień zwykłych stringów
        ...

Dodanie nowego dostawcy = nowa klasa dziedzicząca po LLMProvider + wpis w create_provider().
SDK importowane są leniwie, więc do działania wystarczy pakiet tylko wybranego dostawcy.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
import json
import re
from typing import Any, Iterator, Sequence

from config import CHAT_TEMPERATURE, SUPPORTED_PROVIDERS, Config, load_config

# Neutralny format wiadomości w historii czatu: {"role": "user" | "assistant", "content": "..."}
ChatMessage = dict[str, str]


# --- Błędy ----------------------------------------------------------------
class LLMError(Exception):
    """Błąd warstwy LLM. `user_message` (opcjonalny) jest pokazywany graczu wprost
    przez error_handler.build_user_error_message()."""

    def __init__(self, message: str, *, user_message: str | None = None):
        super().__init__(message)
        self.user_message = user_message


class LLMConfigError(LLMError):
    """Zła lub niepełna konfiguracja dostawcy (brak klucza, brak pakietu, zła nazwa)."""


# --- Interfejsy -----------------------------------------------------------
class ChatSession(ABC):
    """Rozmowa z zachowaną historią (system prompt + kolejne tury)."""

    @abstractmethod
    def send_message_stream(self, text: str) -> Iterator[str]:
        """Wysyła wiadomość i zwraca iterator kolejnych fragmentów odpowiedzi (str).

        Błędy API są zgłaszane jako wyjątki podczas iteracji. Historia sesji
        zostaje uzupełniona dopiero po poprawnym zakończeniu strumienia.
        """


class LLMProvider(ABC):
    """Wspólny interfejs dostawców LLM."""

    name: str = "LLM"

    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    def generate_text(
        self,
        contents: str,
        *,
        system_instruction: str | None = None,
        json_schema: dict[str, Any] | None = None,
        temperature: float | None = None,
        timeout_ms: int | None = None,
    ) -> str:
        """Jednorazowe zapytanie. Z `json_schema` model ma zwrócić JSON zgodny ze schematem."""

    @abstractmethod
    def start_chat(
        self,
        system_instruction: str,
        *,
        history: Sequence[ChatMessage] | None = None,
        temperature: float = CHAT_TEMPERATURE,
    ) -> ChatSession:
        """Tworzy sesję czatu, opcjonalnie kontynuującą wcześniejszą historię."""


def history_from_clean(clean_chat_history: Sequence[dict[str, str]]) -> list[ChatMessage]:
    """Zamienia historię z gry ({"sender", "text"}) na neutralny format ({"role", "content"}).

    Wiadomości gracza mają nadawcę "Me"; wszystko inne (Mistrz Gry, towarzysz) to odpowiedzi modelu.
    """
    return [
        {
            "role": "user" if msg["sender"] == "Me" else "assistant",
            "content": msg["text"],
        }
        for msg in clean_chat_history
    ]


# --- Gemini ---------------------------------------------------------------
class _GeminiChatSession(ChatSession):
    def __init__(self, chat: Any):
        self._chat = chat

    def send_message_stream(self, text: str) -> Iterator[str]:
        for chunk in self._chat.send_message_stream(text):
            if chunk.text:
                yield chunk.text


class GeminiProvider(LLMProvider):
    name = "Gemini"

    def __init__(self, api_key: str, model: str, *, client: Any = None):
        super().__init__(model)
        from google import genai
        from google.genai import types

        self._types = types
        self._client = client or genai.Client(api_key=api_key)

    def generate_text(
        self,
        contents: str,
        *,
        system_instruction: str | None = None,
        json_schema: dict[str, Any] | None = None,
        temperature: float | None = None,
        timeout_ms: int | None = None,
    ) -> str:
        types = self._types
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            response_mime_type="application/json" if json_schema else None,
            response_json_schema=json_schema,
            http_options=types.HttpOptions(timeout=timeout_ms) if timeout_ms else None,
        )
        response = self._client.models.generate_content(
            model=self.model, contents=contents, config=config
        )
        return response.text or ""

    def start_chat(
        self,
        system_instruction: str,
        *,
        history: Sequence[ChatMessage] | None = None,
        temperature: float = CHAT_TEMPERATURE,
    ) -> ChatSession:
        types = self._types
        gemini_history = [
            types.Content(
                role="user" if msg["role"] == "user" else "model",
                parts=[types.Part.from_text(text=msg["content"])],
            )
            for msg in (history or [])
        ]
        chat = self._client.chats.create(
            model=self.model,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
            ),
            history=gemini_history or None,
        )
        return _GeminiChatSession(chat)


# --- OpenAI-compatible (OpenRouter, Ollama) ---------------------------------
_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)


def _strip_code_fences(text: str) -> str:
    """Część modeli owija JSON w ```json ... ``` mimo prośby o czysty JSON."""
    match = _FENCE_RE.match(text)
    return match.group(1) if match else text


class _OpenAIChatSession(ChatSession):
    def __init__(
        self,
        provider: "OpenAICompatibleProvider",
        system_instruction: str,
        history: Sequence[ChatMessage],
        temperature: float,
    ):
        self._provider = provider
        self._system = system_instruction
        self._history: list[ChatMessage] = [dict(m) for m in history]
        self._temperature = temperature

    def send_message_stream(self, text: str) -> Iterator[str]:
        provider = self._provider
        messages: list[ChatMessage] = []
        if self._system:
            messages.append({"role": "system", "content": self._system})
        messages.extend(self._history)
        messages.append({"role": "user", "content": text})

        parts: list[str] = []
        with provider._translate_errors():
            stream = provider._client.chat.completions.create(
                model=provider.model,
                messages=messages,
                temperature=self._temperature,
                stream=True,
            )
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    parts.append(delta)
                    yield delta

        reply = "".join(parts)
        if reply.strip():  # historia rośnie tylko po udanej, niepustej turze
            self._history.append({"role": "user", "content": text})
            self._history.append({"role": "assistant", "content": reply})


class OpenAICompatibleProvider(LLMProvider):
    """Dostawca dla API zgodnych z OpenAI Chat Completions (OpenRouter, Ollama, ...)."""

    def __init__(
        self,
        name: str,
        model: str,
        base_url: str,
        api_key: str,
        *,
        timeout_ms: int | None = None,
        connection_hint: str = "Sprawdź połączenie z internetem.",
        client: Any = None,
    ):
        super().__init__(model)
        self.name = name
        self._base_url = base_url
        self._connection_hint = connection_hint
        if client is None:
            from openai import OpenAI

            kwargs: dict[str, Any] = {}
            if timeout_ms:
                kwargs["timeout"] = timeout_ms / 1000
            # max_retries=0: SDK nie ponawia po cichu zapytań (429/5xx) – błędy trafiają od razu
            # do error_handler, tak jak przy Gemini.
            client = OpenAI(api_key=api_key, base_url=base_url, max_retries=0, **kwargs)
        self._client = client

    @contextmanager
    def _translate_errors(self) -> Iterator[None]:
        import openai

        try:
            yield
        except openai.APITimeoutError:
            raise  # komunikat "Request timed out." jest rozpoznawany jako timeout
        except openai.APIConnectionError as error:
            raise LLMError(
                str(error),
                user_message=(
                    f"❌ Nie można połączyć się z {self.name} ({self._base_url}).\n"
                    f"• {self._connection_hint}"
                ),
            ) from error

    def generate_text(
        self,
        contents: str,
        *,
        system_instruction: str | None = None,
        json_schema: dict[str, Any] | None = None,
        temperature: float | None = None,
        timeout_ms: int | None = None,
    ) -> str:
        import openai

        system = system_instruction or ""
        if json_schema:
            # Nie każdy model respektuje response_format, więc schemat podajemy też w prompcie.
            system = (
                (system + "\n\n" if system else "")
                + "Odpowiedz WYŁĄCZNIE poprawnym JSON-em (bez komentarzy i bez bloków ```) "
                + "zgodnym z tym schematem JSON:\n"
                + json.dumps(json_schema, ensure_ascii=False)
            )
        messages: list[ChatMessage] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": contents})

        kwargs: dict[str, Any] = {"model": self.model, "messages": messages}
        if temperature is not None:
            kwargs["temperature"] = temperature
        if timeout_ms:
            kwargs["timeout"] = timeout_ms / 1000

        with self._translate_errors():
            if json_schema:
                response_format = {
                    "type": "json_schema",
                    "json_schema": {"name": "response", "schema": json_schema},
                }
                try:
                    response = self._client.chat.completions.create(
                        response_format=response_format, **kwargs
                    )
                except openai.BadRequestError:
                    # Model/dostawca nie wspiera response_format – liczymy na schemat z promptu.
                    response = self._client.chat.completions.create(**kwargs)
            else:
                response = self._client.chat.completions.create(**kwargs)

        text = response.choices[0].message.content or ""
        return _strip_code_fences(text) if json_schema else text

    def start_chat(
        self,
        system_instruction: str,
        *,
        history: Sequence[ChatMessage] | None = None,
        temperature: float = CHAT_TEMPERATURE,
    ) -> ChatSession:
        return _OpenAIChatSession(self, system_instruction, history or [], temperature)


# --- Fabryka ----------------------------------------------------------------
def create_provider(settings: Config | None = None) -> LLMProvider:
    """Tworzy dostawcę wskazanego w konfiguracji (LLM_PROVIDER).

    Zgłasza LLMConfigError z czytelnym `user_message`, gdy brakuje klucza, pakietu
    albo nazwa dostawcy jest nieznana.
    """
    settings = settings or load_config()
    kind = settings.provider

    if kind not in SUPPORTED_PROVIDERS:
        raise LLMConfigError(
            f"Nieznany dostawca LLM: {kind!r}",
            user_message=(
                f"❌ Nieznany dostawca LLM: „{kind}”. "
                f"Ustaw LLM_PROVIDER na jedną z wartości: {', '.join(SUPPORTED_PROVIDERS)}."
            ),
        )
    if not isinstance(settings.model, str) or not settings.model.strip():
        raise LLMConfigError("Nazwa modelu nie może być pusta.")

    if kind == "gemini":
        if not settings.api_key:
            raise LLMConfigError(
                "Brak klucza GEMINI_API_KEY w konfiguracji.",
                user_message="❌ Brak klucza GEMINI_API_KEY. Ustaw go w pliku .env lub w zmiennych środowiskowych.",
            )
        try:
            return GeminiProvider(settings.api_key, settings.model)
        except ImportError as error:
            raise LLMConfigError(
                f"Brak pakietu google-genai: {error}",
                user_message="❌ Brak pakietu google-genai. Zainstaluj go: pip install google-genai",
            ) from error

    # OpenRouter i Ollama korzystają z tego samego pakietu `openai` (API zgodne z OpenAI)
    if kind == "openrouter":
        if not settings.api_key:
            raise LLMConfigError(
                "Brak klucza OPENROUTER_API_KEY w konfiguracji.",
                user_message="❌ Brak klucza OPENROUTER_API_KEY. Ustaw go w pliku .env lub w zmiennych środowiskowych.",
            )
        name, api_key = "OpenRouter", settings.api_key
        base_url = settings.base_url or "https://openrouter.ai/api/v1"
        hint = "Sprawdź połączenie z internetem."
    else:  # ollama
        name, api_key = "Ollama", settings.api_key or "ollama"  # klucz jest ignorowany, ale SDK wymaga stringa
        hint = "Upewnij się, że Ollama jest uruchomiona (ollama serve) i że model jest pobrany (ollama pull <model>)."

    try:
        return OpenAICompatibleProvider(
            name,
            settings.model,
            settings.base_url or "",
            api_key,
            timeout_ms=settings.timeout_ms,
            connection_hint=hint,
        )
    except ImportError as error:
        raise LLMConfigError(
            f"Brak pakietu openai: {error}",
            user_message="❌ Brak pakietu openai. Zainstaluj go: pip install openai",
        ) from error
