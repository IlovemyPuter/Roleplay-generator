import json
import os

from google import genai
from google.genai import types
from pydantic import ValidationError

from character import Character, validate_character_response

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
SYSTEM_INSTRUCTION_PATH = os.path.join(
    os.path.dirname(__file__), "prompts", "generate-character.system.md"
)


def generate_character(
    description: str,
    client: genai.Client,
    *,
    model: str | None = DEFAULT_MODEL,
    max_attempts: int = 2,
) -> Character:
    """Generuje i waliduje postać na podstawie opisu gracza."""
    description = description.strip()
    if not description:
        raise ValueError("Opis postaci nie może być pusty.")

    with open(SYSTEM_INSTRUCTION_PATH, encoding="utf-8") as instruction_file:
        system_instruction = instruction_file.read()

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


if __name__ == "__main__":
    import sys

    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit(
            "Brak GEMINI_API_KEY. Ustaw klucz w pliku .env lub w środowisku."
        )

    description = " ".join(sys.argv[1:]).strip() or input("Opis postaci: ")
    character = generate_character(
        description,
        genai.Client(api_key=api_key),
        model=os.getenv("GEMINI_MODEL", DEFAULT_MODEL),
    )
    print(json.dumps(character.model_dump(), ensure_ascii=False, indent=2))
