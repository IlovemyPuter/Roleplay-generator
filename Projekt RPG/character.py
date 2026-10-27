from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field


CharacterText = Annotated[str, Field(min_length=1)]


class Character(BaseModel):
    """Model postaci zgodny z sześcioma polami aktualnego szablonu."""

    model_config = ConfigDict(
        extra="forbid", strict=True, str_strip_whitespace=True
    )

    name: CharacterText = Field(description="The character's name.")
    role_and_background: CharacterText = Field(
        description="One or two sentences describing the role, setting and relevant background."
    )
    personality: CharacterText = Field(
        description="Behavioral traits, motives or values, and reactions under pressure."
    )
    conversation_style: CharacterText = Field(
        description="Tone, formality, typical reply length and distinctive verbal habits."
    )
    knowledge_and_limits: CharacterText = Field(
        description="Relevant expertise and facts the character cannot know without evidence."
    )
    example_dialogue: CharacterText = Field(
        description="One complete dialogue block with two short player/character exchanges, including speaker labels."
    )


def validate_character_response(response_text: str) -> Character:
    """Odczytaj JSON i sprawdź pola; nieprawidłowy wynik zgłasza ValidationError."""
    return Character.model_validate_json(response_text)
