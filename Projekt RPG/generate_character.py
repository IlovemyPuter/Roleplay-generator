import json

from google import genai
from google.genai import types
from pydantic import ValidationError

from character import Character, validate_character_response
from config import (
    CHARACTER_GENERATION_MAX_ATTEMPTS,
    CHARACTER_SYSTEM_INSTRUCTION_PATH,
    load_config,
)


def generate_character(
    description: str,
    client: genai.Client,
    *,
    model: str | None = None,
    max_attempts: int = CHARACTER_GENERATION_MAX_ATTEMPTS,
) -> Character:
    """Generuje i waliduje postać na podstawie opisu gracza."""
    description = description.strip()
    if not description:
        raise ValueError("Opis postaci nie może być pusty.")
    if model is None:
        model = load_config().model
    if not isinstance(model, str) or not model.strip():
        raise ValueError("Nazwa modelu nie może być pusta.")

    system_instruction = CHARACTER_SYSTEM_INSTRUCTION_PATH.read_text(encoding="utf-8")

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_json_schema=Character.model_json_schema(),
    )
    contents = json.dumps({"player_description": description}, ensure_ascii=False)
    last_error = None

    for _ in range(max_attempts):
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        try:
            return validate_character_response(response.text or "")
        except ValidationError as error:
            last_error = error
            contents = json.dumps(
                {
                    "player_description": description,
                    "previous_response": response.text or "",
                    "validation_errors": str(error),
                },
                ensure_ascii=False,
            )

    raise Exception(
        f"Brak poprawnej postaci po {max_attempts} próbach."
    ) from last_error