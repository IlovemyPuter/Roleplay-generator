from turning_point import (
    TurningPoint,
    get_pending_turning_points,
    is_ready,
    mark_executed,
)


def process_turn(
    game_state: dict[str, int | str | None],
    turning_points: list[TurningPoint],
) -> list[str]:
    effects = []

    for point in get_pending_turning_points(turning_points):
        if is_ready(point, game_state, all_turning_points=turning_points):
            mark_executed(point)
            effects.append(point.effect)

    game_state["ostatni_rzut"] = None
    
    # Aktualizacja zmiennej etapu po ewentualnym zaliczeniu punktu zwrotnego
    update_game_stage(game_state, turning_points)
    
    return effects

def update_game_stage(game_state: dict, turning_points: list[TurningPoint]) -> str:
    """Aktualizuje i zwraca aktualny etap rozgrywki na podstawie punktów zwrotnych."""
    if not turning_points:
        stage = "Swobodna rozgrywka"
        game_state["etap"] = stage
        return stage

    total = len(turning_points)
    # Szukamy pierwszego oczekującego punktu zwrotnego
    for tp in turning_points:
        if tp.status == "oczekujacy":
            stage = f"Etap {tp.id}"
            game_state["etap"] = stage
            return stage

    # Jeśli wszystkie punkty mają status 'wykonany'
    stage = f"Finał ({total}/{total} ukończone)"
    game_state["etap"] = stage
    return stage
