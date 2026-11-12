from typing import Annotated

from pydantic import Field, RootModel, model_validator

from turning_point import TurningPoint


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
