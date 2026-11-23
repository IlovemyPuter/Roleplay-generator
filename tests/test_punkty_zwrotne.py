from turning_point import Condition, TurningPoint, is_ready
from turn_processing import process_turn
import main

def utworz_punkt(typ, wartosc, skutek="Skutek", identyfikator=1):
    return TurningPoint(
        id=identyfikator,
        title="Test",
        description="Opis",
        condition=Condition(type=typ, value=wartosc),
        effect=skutek,
        status="oczekujacy",
    )


def test_tura_spelnia_prog_ale_punkt_czeka_na_sygnal_fabularny():
    stan_gry = {"tura": 1, "ostatni_rzut": None}
    punkt = utworz_punkt("tura", 1)

    assert is_ready(punkt, stan_gry) is True
    assert process_turn(stan_gry, [punkt]) == []
    assert stan_gry == {"tura": 1, "ostatni_rzut": None}
    assert punkt.status == "oczekujacy"


def test_tura_za_wczesnie_nie_spelnia_warunku():
    stan_gry = {"tura": 1, "ostatni_rzut": None}
    punkt = utworz_punkt("tura", 2)

    assert is_ready(punkt, stan_gry) is False
    assert process_turn(stan_gry, [punkt]) == []
    assert stan_gry == {"tura": 1, "ostatni_rzut": None}
    assert punkt.status == "oczekujacy"


def test_rzut_spelnia_prog_ale_punkt_czeka_na_sygnal_fabularny():
    stan_gry = {"tura": 0, "ostatni_rzut": 12}
    punkt = utworz_punkt("rzut", 12)

    assert is_ready(punkt, stan_gry) is True
    assert process_turn(stan_gry, [punkt]) == []
    assert stan_gry["ostatni_rzut"] == 12
    assert punkt.status == "oczekujacy"


def test_rzut_none_nie_spelnia_warunku():
    stan_gry = {"tura": 0, "ostatni_rzut": None}
    punkt = utworz_punkt("rzut", 1)

    assert is_ready(punkt, stan_gry) is False
    assert process_turn(stan_gry, [punkt]) == []
    assert stan_gry["ostatni_rzut"] is None
    assert punkt.status == "oczekujacy"


def test_dwa_punkty_z_rzutem_sa_obslugiwane_sekwencyjnie():
    stan_gry = {"tura": 0, "ostatni_rzut": 14}
    punkty = [
        utworz_punkt("rzut", 10, "Pierwszy", 1),
        utworz_punkt("rzut", 14, "Drugi", 2),
    ]

    assert is_ready(punkty[0], stan_gry, punkty) is True
    assert is_ready(punkty[1], stan_gry, punkty) is False
    assert process_turn(stan_gry, punkty) == []
    assert stan_gry["ostatni_rzut"] == 14
    assert all(punkt.status == "oczekujacy" for punkt in punkty)


def test_sprawdzanie_gotowosci_nie_zmienia_stanu_gry():
    stan_gry = {"tura": 3, "ostatni_rzut": 12}
    stan_przed = stan_gry.copy()
    punkt = utworz_punkt("rzut", 10)

    assert is_ready(punkt, stan_gry) is True
    assert stan_gry == stan_przed

def _make_chat_stub(turning_points, game_state):
    app = main.HybridGMRoleplayChatApp.__new__(main.HybridGMRoleplayChatApp)
    app.turning_points = turning_points
    app.game_state = game_state
    app.has_unsaved_changes = False
    app.update_turning_points_ui = lambda: None
    return app


def test_extract_and_complete_turning_points_respects_turn_threshold():
    punkt = TurningPoint(
        id=1,
        title="Pierwszy cel",
        description="Opis celu",
        condition=Condition(type="tura", value=2),
        effect="Skutek",
        status="oczekujacy",
    )
    stan_gry = {"tura": 1, "ostatni_rzut": None}
    app = _make_chat_stub([punkt], stan_gry)

    # 1. Za niska tura (1 < 2): tag GM zostaje usunięty z tekstu, ale punkt nie może być zaliczony
    cleaned_early = app._extract_and_complete_turning_points(
        "Narracja GM przed czasem. [PUNKT_ZALICZONY: 1]"
    )
    assert cleaned_early == "Narracja GM przed czasem."
    assert punkt.status == "oczekujacy"
    assert stan_gry["tura"] == 1

    # 2. Próg osiągnięty (2 >= 2) + tag GM: punkt przechodzi na 'wykonany', a licznik tur zeruje się
    stan_gry["tura"] = 2
    cleaned_ready = app._extract_and_complete_turning_points(
        "Cel osiągnięty! [PUNKT_ZALICZONY: 1]"
    )
    assert cleaned_ready == "Cel osiągnięty!"
    assert punkt.status == "wykonany"
    assert stan_gry["tura"] == 0
    assert app.has_unsaved_changes is True