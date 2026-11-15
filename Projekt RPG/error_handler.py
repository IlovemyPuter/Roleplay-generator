import json
import math
import re
from pydantic import ValidationError


def format_retry_time(error_str: str) -> str:
    """Wyciąga z komunikatu błędu 429 czas oczekiwania, np. '17s' lub '16h56m40s'."""
    match = (
        re.search(r"retry in\s+(\d[0-9hms.]*)", error_str, re.IGNORECASE)
        or re.search(r"retryDelay\W+(\d[0-9hms.]*)", error_str)
    )
    if not match:
        return "nieznany czas"
    value = match.group(1).rstrip(".")
    only_seconds = re.fullmatch(r"(\d+(?:\.\d+)?)s", value)
    if only_seconds:
        return f"{math.ceil(float(only_seconds.group(1)))}s"
    return value or "nieznany czas"


def classify_api_error(error: Exception) -> str:
    """Zwraca rodzaj błędu: limit, json, klucz, przeciazenie, timeout albo inny."""
    text = str(error)
    upper = text.upper()
    if re.search(r"\b429\b", text) or "RESOURCE_EXHAUSTED" in upper:
        return "limit"
    if isinstance(error, (json.JSONDecodeError, ValidationError)) or "JSON" in upper or "ZARYS" in upper:
        return "json"
    if re.search(r"\b400\b", text) or "API_KEY_INVALID" in upper or "API KEY NOT VALID" in upper:
        return "klucz"
    if re.search(r"\b503\b", text) or "UNAVAILABLE" in upper:
        return "przeciazenie"
    if re.search(r"\b504\b", text) or "DEADLINE_EXCEEDED" in upper or "TIMEOUT" in upper or "TIMED OUT" in upper:
        return "timeout"
    return "inny"


def build_user_error_message(error: Exception) -> str:
    """Zamienia wyjątek API na sformatowany komunikat gotowy do wyświetlenia w oknie czatu."""
    user_message = getattr(error, "user_message", None)
    if isinstance(user_message, str) and user_message.strip():
        return user_message.strip()

    error_str = str(error)
    kind = classify_api_error(error)

    if kind == "limit":
        return (
            "⏳ Wyczerpano limit zapytań do API (błąd 429)\n"
            f"• Limit odnowi się za: {format_retry_time(error_str)}\n"
            "• Gra nie została przerwana. Możesz ją zapisać (F5) i wrócić do niej później.\n\n"
            "🛠️ Jak obejść ten problem?\n"
            "1. Płatny plan: w Google AI Studio przejdź na plan Pay-as-you-go.\n"
            "2. Inne konto: wygeneruj klucz API na innym koncie Google i podmień go w aplikacji.\n"
            "3. Inny model: zmień model na taki, który ma osobną pulę zapytań."
        )
    elif kind == "json":
        details = error_str.strip().replace("\n", " ")
        if len(details) > 200:
            details = details[:200] + "…"
        return (
            "⚠️ Model zwrócił odpowiedź w niepoprawnym formacie (błąd JSON)\n"
            "• Aplikacja ponowiła zapytanie kilka razy, ale odpowiedź nadal była niepoprawna.\n"
            f"• Szczegóły: {details}\n\n"
            "🛠️ Spróbuj ponownie za chwilę. Gra nie została przerwana."
        )
    elif kind == "klucz":
        return (
            "❌ Niepoprawny klucz API (błąd 400)\n"
            "• Podany klucz API jest nieważny lub został błędnie wpisany.\n\n"
            "🛠️ Jak to naprawić?\n"
            "1. Wejdź na stronę Google AI Studio (aistudio.google.com).\n"
            "2. Wygeneruj nowy klucz API.\n"
            "3. Upewnij się, że poprawnie ustawiłeś zmienną środowiskową GEMINI_API_KEY."
        )
    elif kind == "przeciazenie":
        return (
            "⚠️ Model Gemini jest obecnie mocno obciążony (błąd 503). "
            "To chwilowy problem po stronie Google. Spróbuj wysłać wiadomość ponownie za kilka sekund."
        )
    elif kind == "timeout":
        return (
            "⚠️ Model nie odpowiedział w oczekiwanym czasie. "
            "Sprawdź połączenie z internetem i spróbuj wysłać wiadomość ponownie."
        )

    return f"Wystąpił błąd podczas komunikacji z API: {error}"