from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator


PlotText = Annotated[str, Field(min_length=1)]


class Condition(BaseModel):
    """Model warunku wykonania punktu fabularnego"""

    model_config = ConfigDict(extra="forbid", strict=True, serialize_by_alias=True)

    type: Literal["rzut", "tura"] = Field(alias="typ")
    value: int = Field(alias="wartosc")


class TurningPoint(BaseModel):
    """Model punktu fabularnego"""

    model_config = ConfigDict(
        extra="forbid", strict=True, str_strip_whitespace=True, serialize_by_alias=True
    )

    id: Annotated[int, Field(ge=1, le=5)]
    title: PlotText = Field(alias="tytul")
    description: PlotText = Field(alias="opis")
    condition: Condition = Field(alias="warunek")
    effect: PlotText = Field(alias="skutek")
    status: Literal["oczekujacy", "wykonany"] = Field(alias="stan")


class PlotOutline(RootModel[list[TurningPoint]]):
    """Model zarysu fabuły, zawierający pięć punktów fabularnych"""

    root: Annotated[list[TurningPoint], Field(min_length=5, max_length=5)]

    @model_validator(mode="after")
    def require_unique_ids(self) -> "PlotOutline":
        if {point.id for point in self.root} != {1, 2, 3, 4, 5}:
            raise ValueError("Punkty muszą mieć unikalne id od 1 do 5.")
        return self


def validate_plot_response(response_text: str) -> PlotOutline:
    """Sprawdza JSON i pełny kontrakt; W przypadku błędów zgłasza ValidationError."""
    return PlotOutline.model_validate_json(response_text)
