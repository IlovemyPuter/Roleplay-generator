from turning_point import (
    TurningPoint,
    get_pending_turning_points,
    is_ready,
    mark_executed,
)


def process_turn(game_state, turning_points):
    """Przetwarza turę i sprawdza warunki wyłącznie dla pierwszego oczekującego punktu."""
    skutki = []
    
    # Bierzemy pod uwagę TYLKO PIERWSZY napotkany punkt o statusie "oczekujacy"
    current_tp = None
    for tp in turning_points:
        if tp.status == "oczekujacy":
            current_tp = tp
            break

    if not current_tp:
        return skutki

    cond = current_tp.condition
    cond_type = cond.get("type") if isinstance(cond, dict) else getattr(cond, "type", None)
    cond_val = cond.get("value") if isinstance(cond, dict) else getattr(cond, "value", None)

    is_satisfied = False
    if cond_type == "tura":
        if game_state.get("tura", 0) >= cond_val:
            is_satisfied = True
    elif cond_type == "rzut":
        ostatni_rzut = game_state.get("ostatni_rzut")
        if ostatni_rzut is not None and ostatni_rzut >= cond_val:
            is_satisfied = True

    # Jeśli warunek mechaniczny minął, ale czekamy jeszcze na fabularny sygnał GM-a,
    # gra nie zalicza punktu "w ciemno", lecz pozwala GM-owi kontrolować moment wysłania znacznika.
    return skutki


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
    stage = f"Finał"
    game_state["etap"] = stage
    return stage
