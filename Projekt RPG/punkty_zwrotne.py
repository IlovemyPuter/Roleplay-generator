from pydantic import ValidationError

from plot_outline import TurningPoint


def stworz_zadanie_fabularne(id_p, tytul, opis, typ_w, wartosc_w, skutek):
    return {
        "id": id_p,
        "tytul": tytul,
        "opis": opis,
        "warunek": {"typ": typ_w, "wartosc": wartosc_w},
        "skutek": skutek,
        "stan": "oczekujacy"
    }

def zweryfikuj_wpis(punkt):
    if not isinstance(punkt, dict):
        return False
    try:
        TurningPoint.model_validate(punkt)
    except ValidationError:
        return False
    return True

def sprawdz_warunek(punkt, stan_gry):
    if punkt.get("stan") != "oczekujacy":
        return False
        
    warunek = punkt.get("warunek")
    if not isinstance(warunek, dict):
        return False
        
    typ = warunek.get("typ")
    wartosc = warunek.get("wartosc")
    
    if typ == "tura":
        if "tura" not in stan_gry:
            return False
        return stan_gry["tura"] >= wartosc
        
    if typ == "rzut":
        if "ostatni_rzut" not in stan_gry or stan_gry["ostatni_rzut"] is None:
            return False
        wynik = stan_gry["ostatni_rzut"]
        return wynik >= wartosc
        
    return False

def wykonaj_punkt(punkt):
    if punkt.get("stan") == "wykonany":
        return None
    punkt["stan"] = "wykonany"
    return punkt.get("skutek", "")

def pobierz_oczekujace(lista_punktow):
    return [punkt for punkt in lista_punktow if punkt.get("stan") == "oczekujacy"]
