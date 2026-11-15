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


def is_ready(point: TurningPoint, game_state: dict, all_turning_points: list[TurningPoint] = None) -> bool:
    """Sprawdza, czy punkt jest gotowy do wykonania.
    Warunki:
    - Punkt musi mieć status 'oczekujacy'.
    - Musi być pierwszym z nierozwiązanych punktów (sekwencyjność: żaden punkt nie może się wykonać, dopóki poprzedni nie jest zaliczony).
    - Spełnione muszą być kryteria tur lub rzutów.
    """
    if point.status != "oczekujacy":
        return False

    # Sprawdzenie sekwencyjności: czy wszystkie wcześniejsze punkty są już wykonane
    if all_turning_points:
        for p in all_turning_points:
            if p.id < point.id and p.status != "wykonany":
                return False  # Poprzedni punkt nie jest jeszcze zaliczony, więc ten stoi w miejscu!

    # Sprawdzenie warunków (tura / rzut)
    cond = point.condition
    if cond.type == "tura":
        current_turn = game_state.get("tura", 0)
        return current_turn >= cond.value
    elif cond.type == "rzut":
        last_roll = game_state.get("ostatni_rzut")
        if last_roll is None:
            return False
        return last_roll >= cond.value

    return False


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
