from turning_point import Condition, TurningPoint
from turn_processing import process_turn


def utworz_punkt(typ, wartosc, skutek="Skutek", identyfikator=1):
    return TurningPoint(
        id=identyfikator,
        title="Test",
        description="Opis",
        condition=Condition(type=typ, value=wartosc),
        effect=skutek,
        status="oczekujacy",
    )


def test_tura_spelnia_prog():
    stan_gry = {"tura": 0, "ostatni_rzut": None}
    punkt = utworz_punkt("tura", 1)

    assert process_turn(stan_gry, [punkt]) == ["Skutek"]
    assert stan_gry == {"tura": 1, "ostatni_rzut": None}
    assert punkt.status == "wykonany"


def test_tura_za_wczesnie():
    stan_gry = {"tura": 0, "ostatni_rzut": None}
    punkt = utworz_punkt("tura", 2)

    assert process_turn(stan_gry, [punkt]) == []
    assert stan_gry == {"tura": 1, "ostatni_rzut": None}
    assert punkt.status == "oczekujacy"


def test_rzut_spelnia_prog():
    stan_gry = {"tura": 0, "ostatni_rzut": 12}
    punkt = utworz_punkt("rzut", 12)

    assert process_turn(stan_gry, [punkt]) == ["Skutek"]
    assert stan_gry["ostatni_rzut"] is None
    assert punkt.status == "wykonany"


def test_rzut_none_nie_spelnia_warunku():
    stan_gry = {"tura": 0, "ostatni_rzut": None}
    punkt = utworz_punkt("rzut", 1)

    assert process_turn(stan_gry, [punkt]) == []
    assert stan_gry["ostatni_rzut"] is None
    assert punkt.status == "oczekujacy"


def test_dwa_punkty_z_rzutem_widzą_ten_sam_rzut():
    stan_gry = {"tura": 0, "ostatni_rzut": 14}
    punkty = [
        utworz_punkt("rzut", 10, "Pierwszy", 1),
        utworz_punkt("rzut", 14, "Drugi", 2),
    ]

    assert process_turn(stan_gry, punkty) == ["Pierwszy", "Drugi"]
    assert stan_gry["ostatni_rzut"] is None
    assert all(punkt.status == "wykonany" for punkt in punkty)


def test_sprawdzanie_warunku_nie_zmienia_stanu_gry():
    from turning_point import is_ready

    stan_gry = {"tura": 3, "ostatni_rzut": 12}
    stan_przed = stan_gry.copy()
    punkt = utworz_punkt("rzut", 10)

    assert is_ready(punkt, stan_gry) is True
    assert stan_gry == stan_przed
