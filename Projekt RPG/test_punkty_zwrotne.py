from punkty_zwrotne import (
    obsluz_ture,
    sprawdz_warunek,
    stworz_zadanie_fabularne,
)


def utworz_punkt(typ, wartosc, skutek="Skutek"):
    return stworz_zadanie_fabularne(
        1, "Test", "Opis", typ, wartosc, skutek
    )


def test_tura_spelnia_prog():
    stan_gry = {"tura": 0, "ostatni_rzut": None}
    punkt = utworz_punkt("tura", 1)

    assert obsluz_ture(stan_gry, [punkt]) == ["Skutek"]
    assert stan_gry == {"tura": 1, "ostatni_rzut": None}
    assert punkt["stan"] == "wykonany"


def test_tura_za_wczesnie():
    stan_gry = {"tura": 0, "ostatni_rzut": None}
    punkt = utworz_punkt("tura", 2)

    assert obsluz_ture(stan_gry, [punkt]) == []
    assert stan_gry == {"tura": 1, "ostatni_rzut": None}
    assert punkt["stan"] == "oczekujacy"


def test_rzut_spelnia_prog():
    stan_gry = {"tura": 0, "ostatni_rzut": 12}
    punkt = utworz_punkt("rzut", 12)

    assert obsluz_ture(stan_gry, [punkt]) == ["Skutek"]
    assert stan_gry["ostatni_rzut"] is None
    assert punkt["stan"] == "wykonany"


def test_rzut_none_nie_spelnia_warunku():
    stan_gry = {"tura": 0, "ostatni_rzut": None}
    punkt = utworz_punkt("rzut", 1)

    assert obsluz_ture(stan_gry, [punkt]) == []
    assert stan_gry["ostatni_rzut"] is None
    assert punkt["stan"] == "oczekujacy"


def test_dwa_punkty_z_rzutem_widzą_ten_sam_rzut():
    stan_gry = {"tura": 0, "ostatni_rzut": 14}
    punkty = [utworz_punkt("rzut", 10, "Pierwszy"), utworz_punkt("rzut", 14, "Drugi")]

    assert obsluz_ture(stan_gry, punkty) == ["Pierwszy", "Drugi"]
    assert stan_gry["ostatni_rzut"] is None
    assert all(punkt["stan"] == "wykonany" for punkt in punkty)


def test_brak_pol_warunku_zwraca_false_bez_zmiany_stanu():
    stan_gry = {"tura": 3, "ostatni_rzut": 12}
    kopia_stanu = stan_gry.copy()
    punkt = utworz_punkt("rzut", 10)

    for warunek in ({}, {"typ": "rzut"}, {"wartosc": 10}):
        punkt["warunek"] = warunek
        assert sprawdz_warunek(punkt, stan_gry) is False

    assert stan_gry == kopia_stanu
