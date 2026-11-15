from turning_point import (
    TurningPoint,
    get_pending_turning_points,
    is_ready,
    mark_executed,
)


def process_turn(
    game_state: dict[str, int | None],
    turning_points: list[TurningPoint],
) -> list[str]:
    # Usunięto stąd "game_state['tura'] += 1", ponieważ tura zwiększa się już w main.py
    effects = []

    for point in get_pending_turning_points(turning_points):
        # Przekazujemy całą listę turning_points, aby zadziałała blokada sekwencyjna!
        if is_ready(point, game_state, all_turning_points=turning_points):
            mark_executed(point)
            effects.append(point.effect)

    game_state["ostatni_rzut"] = None
    return effects
