from collections.abc import Iterable, Mapping
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


PlotText = Annotated[str, Field(min_length=1)]


class Condition(BaseModel):
    """Model warunku wykonania punktu fabularnego"""

    model_config = ConfigDict(extra="forbid", strict=True)

    type: Literal["rzut", "tura"]
    value: int


class TurningPoint(BaseModel):
    """Model punktu fabularnego"""

    model_config = ConfigDict(
        extra="forbid", strict=True, str_strip_whitespace=True
    )

    id: Annotated[int, Field(ge=1, le=5)]
    title: PlotText
    description: PlotText
    condition: Condition
    effect: PlotText
    status: Literal["oczekujacy", "wykonany"]


def is_ready(
    point: TurningPoint,
    game_state: Mapping[str, int | None],
) -> bool:
    """Sprawdza stan punktu i próg tury lub ostatniego rzutu kością."""
    if point.status != "oczekujacy":
        return False

    state_key = "tura" if point.condition.type == "tura" else "ostatni_rzut"
    current_value = game_state.get(state_key)
    return current_value is not None and current_value >= point.condition.value


def mark_executed(point: TurningPoint) -> None:
    """Oznacza punkt jako wykonany po pomyślnym zastosowaniu jego skutku."""
    point.status = "wykonany"


def get_pending_turning_points(points: Iterable[TurningPoint]) -> list[TurningPoint]:
    """Zwraca oczekujące punkty bez zmiany ich stanu ani kolejności."""
    return [point for point in points if point.status == "oczekujacy"]


def get_ready_turning_points(
    points: Iterable[TurningPoint],
    game_state: Mapping[str, int | None],
) -> list[TurningPoint]:
    """Zwraca punkty gotowe do wykonania bez oznaczania ich jako wykonane."""
    return [point for point in points if is_ready(point, game_state)]
