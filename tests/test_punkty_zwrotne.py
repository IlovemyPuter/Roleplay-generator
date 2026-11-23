from turning_point import Condition, TurningPoint, is_ready
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
