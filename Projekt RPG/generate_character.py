import json

from pydantic import ValidationError

from character import Character, validate_character_response
from config import (
    CHARACTER_GENERATION_MAX_ATTEMPTS,
    CHARACTER_SYSTEM_INSTRUCTION_PATH,
)
from llm_client import LLMProvider


def generate_character(
    description: str,
    provider: LLMProvider,
    *,
    max_attempts: int = CHARACTER_GENERATION_MAX_ATTEMPTS,
) -> Character:
    """Generuje i waliduje postać na podstawie opisu gracza."""
    description = description.strip()
    if not description:
        raise ValueError("Opis postaci nie może być pusty.")

    system_instruction = CHARACTER_SYSTEM_INSTRUCTION_PATH.read_text(encoding="utf-8")
    json_schema = Character.model_json_schema()

    contents = json.dumps({"player_description": description}, ensure_ascii=False)
    last_error = None

    for _ in range(max_attempts):
        response_text = provider.generate_text(
            contents,
            system_instruction=system_instruction,
            json_schema=json_schema,
        )

        try:
            return validate_character_response(response_text)
        except ValidationError as error:
            last_error = error
            contents = json.dumps(
                {
                    "player_description": description,
                    "previous_response": response_text,
                    "validation_errors": str(error),
                },
                ensure_ascii=False,
            )

    raise Exception(
        f"Brak poprawnej postaci po {max_attempts} próbach."
    ) from last_error
