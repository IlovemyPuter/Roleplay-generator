from contextlib import nullcontext
import json
from typing import Any

from google import genai
from google.genai import types
from pydantic import ValidationError

from character import Character
from config import (
    PLOT_GENERATION_MAX_ATTEMPTS,
    PLOT_REQUEST_TIMEOUT_MS,
    PLOT_SYSTEM_INSTRUCTION_PATH,
    load_config,
)
from plot_outline import PlotOutline, validate_plot_response


def generate_plot(
    setting: str,
    characters: list[dict[str, Any] | Character],
    *,
    model: str | None = None,
    client: genai.Client | None = None,
) -> PlotOutline:
    """Zwraca zweryfikowany zarys z pięcioma oczekującymi punktami zwrotnymi."""
    if not isinstance(setting, str) or not setting.strip():
        raise ValueError("Setting nie może być pusty.")
    settings = load_config()
    if model is None:
        model = settings.model
    if not isinstance(model, str) or not model.strip():
        raise ValueError("Nazwa modelu nie może być pusta.")
    if not isinstance(characters, list) or not characters:
        raise ValueError("Postacie muszą być niepustą listą.")

    character_data = [
        character.model_dump() if isinstance(character, Character) else character
        for character in characters
    ]

    if any(not isinstance(character, dict) or not character for character in character_data):
        raise ValueError("Każda postać musi być niepustym słownikiem lub obiektem Character.")

    request: dict[str, Any] = {"setting": setting, "characters": character_data}
    try:
        contents = json.dumps(request, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError("Dane postaci muszą być zapisane w poprawnym formacie JSON.") from error

    config = types.GenerateContentConfig(
        system_instruction=PLOT_SYSTEM_INSTRUCTION_PATH.read_text(encoding="utf-8"),
        response_mime_type="application/json",
        response_json_schema=PlotOutline.model_json_schema(),
    )

    if client is None and not settings.api_key:
        raise ValueError("Brak klucza GEMINI_API_KEY w konfiguracji.")

    client_context = (
        nullcontext(client)
        if client is not None
        else genai.Client(
            api_key=settings.api_key,
            http_options=types.HttpOptions(timeout=PLOT_REQUEST_TIMEOUT_MS),
        )
    )

    last_error = None
    error_summary = ""

    with client_context as api_client:
        for _ in range(PLOT_GENERATION_MAX_ATTEMPTS):
            response = api_client.models.generate_content(
                model=model, contents=contents, config=config
            )
            response_text = response.text or ""
            try:
                outline = validate_plot_response(response_text)
                for point in outline.root:
                    point.status = "oczekujacy"
                return outline
            except ValidationError as error:
                last_error = error
                feedback = [
                    {
                        "field": ".".join(str(part) for part in item["loc"]) or "$",
                        "error": item["msg"],
                    }
                    for item in error.errors(include_input=False, include_url=False)
                ]
                error_summary = "; ".join(
                    f"{item['field']}: {item['error']}" for item in feedback
                )
                request["previous_response"] = response_text
                request["validation_errors"] = feedback
                contents = json.dumps(request, ensure_ascii=False, allow_nan=False)

    raise Exception(
        f"Brak poprawnego zarysu fabuły po {PLOT_GENERATION_MAX_ATTEMPTS} próbach. "
        f"Ostatnie błędy: {error_summary}"
    ) from last_error
